"""The bank routes, with the GoCardless client replaced by a mock."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from requests import HTTPError

from app.bank.client import GoCardlessBankDataClient, get_bank_client
from app.main import app
from app.models import Account, BankIntegration


@pytest.fixture
def bank(client) -> Mock:
    bank = Mock(spec=GoCardlessBankDataClient)
    bank.get_institutions.return_value = [{"id": "BANK_DK", "name": "Danske Test"}]
    bank.create_requisition.return_value = {"id": "req-1", "link": "https://bank/x"}
    bank.get_requisition.return_value = {"accounts": ["acc-1"]}
    bank.get_account_details.return_value = {
        "account": {"name": "Checking", "iban": "DK01", "currency": "DKK"}
    }
    bank.get_account_balances.return_value = {"balances": []}
    bank.get_account_transactions.return_value = {"transactions": {"booked": []}}
    app.dependency_overrides[get_bank_client] = lambda: bank
    return bank


def add_linked_account(db, name, expires_in_days=60) -> Account:
    now = datetime.now(UTC)
    integration = BankIntegration(
        institution_id="BANK_DK",
        country_code="DK",
        requisition_id=f"req-{name}",
        linked_at=now,
        expires_at=now + timedelta(days=expires_in_days),
    )
    account = Account(
        name=name,
        bank_name="Danske Test",
        currency="DKK",
        external_id=f"ext-{name}",
        bank_integration=integration,
    )
    db.add(account)
    db.commit()
    return account


def test_countries_start_with_denmark(client):
    assert client.get("/api/bank/countries").json()[0]["code"] == "DK"


def test_institutions(client, bank):
    response = client.get("/api/bank/institutions", params={"country": "DK"})

    assert response.json()[0]["name"] == "Danske Test"


def test_link_flow(client, db, bank):
    response = client.post(
        "/api/bank/links",
        json={
            "institution_id": "BANK_DK",
            "country_code": "DK",
            "redirect_url": "http://localhost:5173/link/callback",
        },
    )
    assert response.json() == {"link": "https://bank/x"}
    reference = bank.create_requisition.call_args.kwargs["reference"]

    choices = client.get(f"/api/bank/links/{reference}/accounts").json()
    assert [c["name"] for c in choices] == ["Checking"]

    response = client.post(
        f"/api/bank/links/{reference}/complete", json={"external_ids": ["acc-1"]}
    )
    assert response.status_code == 204

    links = client.get("/api/bank/links").json()
    assert len(links) == 1
    assert links[0]["bank_name"] == "Danske Test"
    assert links[0]["consent_status"] == "ok"


def test_redirect_url_must_be_a_url(client, bank):
    response = client.post(
        "/api/bank/links",
        json={"institution_id": "B", "country_code": "DK", "redirect_url": "nope"},
    )

    assert response.status_code == 422


def test_unknown_reference_is_404(client, bank):
    assert client.get("/api/bank/links/nope/accounts").status_code == 404


def test_link_error_is_400(client, db, bank):
    db.add(
        BankIntegration(
            institution_id="B", country_code="DK", requisition_id="r", reference="ref"
        )
    )
    db.commit()

    response = client.post("/api/bank/links/ref/complete", json={"external_ids": []})

    assert response.status_code == 400
    assert "at least one" in response.json()["detail"]


def test_bank_error_is_502(client, bank):
    bank.get_institutions.side_effect = HTTPError("503 Service Unavailable")

    response = client.get("/api/bank/institutions", params={"country": "DK"})

    assert response.status_code == 502
    assert response.json()["detail"].startswith("Could not list banks")


def test_expiring_link_is_flagged(client, db, bank):
    add_linked_account(db, "Checking", expires_in_days=3)

    assert client.get("/api/bank/links").json()[0]["consent_status"] == "expiring"


def test_sync_reports_per_account_errors(client, db, bank):
    add_linked_account(db, "Broken")
    add_linked_account(db, "Checking")
    add_linked_account(db, "Expired", expires_in_days=-1)

    def transactions(external_id, date_from):
        if external_id == "ext-Broken":
            raise HTTPError("500")
        return {"transactions": {"booked": []}}

    bank.get_account_transactions.side_effect = transactions

    results = {r["account_name"]: r for r in client.post("/api/bank/sync").json()}

    assert results["Broken"]["error"].startswith("Could not fetch transactions")
    assert results["Checking"] == {
        "account_id": results["Checking"]["account_id"],
        "account_name": "Checking",
        "new_transactions": 0,
        "error": None,
    }
    assert results["Expired"]["error"] == "Consent expired: renew the link"
    assert bank.get_account_transactions.call_count == 2
