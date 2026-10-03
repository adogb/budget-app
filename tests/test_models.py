from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import StatementError

from app.models import Account


def add_account(db, last_synced_at) -> Account:
    account = Account(
        name="Checking",
        bank_name="Test Bank",
        currency="DKK",
        last_synced_at=last_synced_at,
    )
    db.add(account)
    db.commit()
    db.expire_all()
    return account


def test_utc_datetime_comes_back_timezone_aware(db):
    copenhagen = timezone(timedelta(hours=2))
    account = add_account(db, datetime(2026, 10, 3, 14, 0, tzinfo=copenhagen))

    synced = account.last_synced_at
    assert synced is not None
    assert synced == datetime(2026, 10, 3, 12, 0, tzinfo=UTC)
    assert synced.tzinfo is UTC


def test_utc_datetime_refuses_naive_values(db):
    with pytest.raises(StatementError, match="Naive datetime"):
        add_account(db, datetime(2026, 10, 3, 12, 0))  # noqa: DTZ001
