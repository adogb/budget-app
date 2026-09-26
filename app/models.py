"""All database tables.

Money columns (`*_minor`) are integers in the currency's minor unit, e.g. øre.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class BankIntegration(Base):
    """One GoCardless bank link (a "requisition")."""

    __tablename__ = "bank_integrations"

    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[str] = mapped_column(String(50))
    country_code: Mapped[str] = mapped_column(String(2))
    requisition_id: Mapped[str] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    iban: Mapped[str | None] = mapped_column(String(34))
    bank_name: Mapped[str] = mapped_column(String(50))
    balance_minor: Mapped[int] = mapped_column(default=0)
    currency: Mapped[str] = mapped_column(String(3))

    transactions: Mapped[list[Transaction]] = relationship(back_populates="account")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    amount_minor: Mapped[int]
    currency: Mapped[str] = mapped_column(String(3))
    description: Mapped[str] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(String(255))
    booking_date: Mapped[date] = mapped_column(Date)
    value_date: Mapped[date | None] = mapped_column(Date)
    bank_transaction_id: Mapped[str | None] = mapped_column(String(100))
    gc_transaction_id: Mapped[str | None] = mapped_column(String(100))

    account: Mapped[Account] = relationship(back_populates="transactions")
