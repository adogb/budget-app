from datetime import date

from app.models import Account, Transaction


def add_account(db, name="Checking") -> Account:
    account = Account(name=name, bank_name="Test Bank", currency="DKK")
    db.add(account)
    db.commit()
    return account


def add_transaction(db, account, booking_date, amount_minor=-2500) -> Transaction:
    transaction = Transaction(
        account_id=account.id,
        amount_minor=amount_minor,
        currency="DKK",
        description="Netto",
        booking_date=booking_date,
    )
    db.add(transaction)
    db.commit()
    return transaction


def test_empty(client):
    response = client.get("/api/transactions")

    assert response.status_code == 200
    assert response.json() == []


def test_lists_newest_first(client, db):
    account = add_account(db)
    add_transaction(db, account, date(2026, 9, 1))
    add_transaction(db, account, date(2026, 9, 3), amount_minor=-1999)

    body = client.get("/api/transactions").json()

    assert [t["booking_date"] for t in body] == ["2026-09-03", "2026-09-01"]
    assert body[0]["amount"] == {"amount": -1999, "currency": "DKK"}


def test_filter_by_account(client, db):
    checking = add_account(db, "Checking")
    shared = add_account(db, "Shared")
    add_transaction(db, checking, date(2026, 9, 1))
    add_transaction(db, shared, date(2026, 9, 2))

    body = client.get("/api/transactions", params={"account_id": shared.id}).json()

    assert [t["account_id"] for t in body] == [shared.id]
