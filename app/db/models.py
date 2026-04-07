# models.py (SQLAlchemy 2.0 style)
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    # Parent class that all the database models inherit from
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )

    categories: Mapped[list[Category]] = relationship(back_populates="user")
    accounts: Mapped[list[Account]] = relationship(back_populates="user")
    bank_integrations: Mapped[list[BankIntegration]] = relationship(
        back_populates="user"
    )


class BankIntegration(Base):
    """
    Stores bank connection information for each user.
    Replaces the config file approach for multi-user support.
    """

    __tablename__ = "bank_integrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Bank identification
    institution_id: Mapped[str] = mapped_column(String(50), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)

    # GoCardless/Nordigen requisition details
    requisition_id: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )

    # Access tokens (in production, these should be encrypted)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    access_valid_days: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=90
    )
    refresh_valid_days: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=90
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False,
    )

    # Relationship
    user: Mapped[User] = relationship(back_populates="bank_integrations")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )

    user: Mapped[User] = relationship(back_populates="categories")
    parent: Mapped[Optional[Category]] = relationship(remote_side="Category.id")
    transactions: Mapped[list[Transaction]] = relationship(back_populates="category")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    external_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, unique=True
    )  # Bank's account ID

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    iban: Mapped[str] = mapped_column(
        String(34), nullable=True
    )  # Made nullable - not all accounts have IBAN
    balance: Mapped[float] = mapped_column(nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="DKK")
    bank_name: Mapped[str] = mapped_column(String(50), nullable=False)

    user: Mapped[User] = relationship(back_populates="accounts")
    transactions: Mapped[list[Transaction]] = relationship(back_populates="account")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )

    # store money in cents as integer to avoid float issues
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="DKK")

    description: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    booking_date: Mapped[date] = mapped_column(Date, nullable=False)
    value_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    bank_transaction_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # Bank's transaction ID
    gc_transaction_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # GoCardless transaction ID

    account: Mapped[Account] = relationship(back_populates="transactions")
    category: Mapped[Optional[Category]] = relationship(back_populates="transactions")
