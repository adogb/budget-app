"""All database tables.

Money columns (`*_minor`) are integers in the currency's minor unit, e.g. øre.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import (
    Date,
    DateTime,
    Dialect,
    ForeignKey,
    MetaData,
    String,
    TypeDecorator,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    # Named constraints, so migrations can drop them again.
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class UTCDateTime(TypeDecorator[datetime]):
    """Stores UTC; always gives back timezone-aware datetimes.

    SQLite has no timezone support, so it would otherwise return naive values.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Naive datetime; use datetime.now(UTC)")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect):
        return None if value is None else value.replace(tzinfo=UTC)


class BankIntegration(Base):
    """One GoCardless bank link (a "requisition")."""

    __tablename__ = "bank_integrations"

    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[str] = mapped_column(String(50))
    country_code: Mapped[str] = mapped_column(String(2))
    requisition_id: Mapped[str] = mapped_column(String(100), unique=True)
    # GoCardless sends this back as ?ref= when the bank redirects to us.
    reference: Mapped[str] = mapped_column(
        String(36), unique=True, default=lambda: str(uuid4())
    )
    # None until the user has chosen accounts, i.e. the link is complete.
    linked_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    accounts: Mapped[list[Account]] = relationship(back_populates="bank_integration")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    iban: Mapped[str | None] = mapped_column(String(34))
    bank_name: Mapped[str] = mapped_column(String(50))
    balance_minor: Mapped[int] = mapped_column(default=0)
    currency: Mapped[str] = mapped_column(String(3))
    bank_integration_id: Mapped[int | None] = mapped_column(
        ForeignKey("bank_integrations.id")
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    bank_integration: Mapped[BankIntegration | None] = relationship(
        back_populates="accounts"
    )
    transactions: Mapped[list[Transaction]] = relationship(back_populates="account")


class Transaction(Base):
    """A booked transaction. Pending ones live in `PendingTransaction`."""

    __tablename__ = "transactions"
    # import_key is the dedup key for bank rows; NULL for manual ones (allowed
    # more than once by SQLite's unique constraint).
    __table_args__ = (UniqueConstraint("account_id", "import_key"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    amount_minor: Mapped[int]
    currency: Mapped[str] = mapped_column(String(3))
    description: Mapped[str] = mapped_column(String(255))
    payee: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(String(255))
    booking_date: Mapped[date] = mapped_column(Date)
    value_date: Mapped[date | None] = mapped_column(Date)
    bank_transaction_id: Mapped[str | None] = mapped_column(String(100))
    gc_transaction_id: Mapped[str | None] = mapped_column(String(100))
    import_key: Mapped[str | None] = mapped_column(String(100))

    account: Mapped[Account] = relationship(back_populates="transactions")


class PendingTransaction(Base):
    """Not yet booked. Replaced for the account on every sync (spec §4)."""

    __tablename__ = "pending_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    amount_minor: Mapped[int]
    currency: Mapped[str] = mapped_column(String(3))
    description: Mapped[str] = mapped_column(String(255))
    payee: Mapped[str | None] = mapped_column(String(255))
    booking_date: Mapped[date | None] = mapped_column(Date)
    value_date: Mapped[date | None] = mapped_column(Date)


class CategoryGroup(Base):
    """A folder of categories, e.g. "Housing" (spec §1).

    Exactly one group has `is_income` set; its categories are where income
    lands. Hidden groups and categories stay in the tree so that anything
    already pointing at them keeps working.
    """

    __tablename__ = "category_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    is_income: Mapped[bool] = mapped_column(default=False)
    hidden: Mapped[bool] = mapped_column(default=False)
    sort_order: Mapped[int] = mapped_column(default=0)

    # Ordered by sort_order, with id breaking ties so the tree can't shuffle
    # between two requests.
    categories: Mapped[list[Category]] = relationship(
        back_populates="group", order_by="Category.sort_order, Category.id"
    )


class Category(Base):
    """One envelope. Always inside a group (spec §1)."""

    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("group_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("category_groups.id"))
    name: Mapped[str] = mapped_column(String(80))
    hidden: Mapped[bool] = mapped_column(default=False)
    sort_order: Mapped[int] = mapped_column(default=0)

    group: Mapped[CategoryGroup] = relationship(back_populates="categories")
