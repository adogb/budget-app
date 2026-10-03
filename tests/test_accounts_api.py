from app.models import Account


def test_lists_accounts(client, db):
    db.add(
        Account(
            name="Checking",
            bank_name="Test Bank",
            iban="DK1234",
            balance_minor=1234550,
            currency="DKK",
        )
    )
    db.commit()

    body = client.get("/api/accounts").json()

    assert body == [
        {
            "id": 1,
            "name": "Checking",
            "bank_name": "Test Bank",
            "iban": "DK1234",
            "balance": {"amount": 1234550, "currency": "DKK"},
            "bank_integration_id": None,
            "last_synced_at": None,
        }
    ]
