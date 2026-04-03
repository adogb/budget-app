# Using TypedDicts for static typing. No Pydantic here — we avoid the
# runtime validation overhead on external API responses. Types exist
# purely for IDE support and static analysis (mypy/pyright).
# Fields marked NotRequired are optional in the GoCardless response.

from typing import NotRequired, TypedDict


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------


class GCAmount(TypedDict):
    """Monetary amount with currency (used in transactions and balances)."""

    amount: str  # e.g. "-10.50"
    currency: str  # ISO 4217, e.g. "EUR"


# ---------------------------------------------------------------------------
# End User Agreement  (POST /agreements/enduser/)
# ---------------------------------------------------------------------------


class GCEndUserAgreement(TypedDict):
    """A GoCardless end-user agreement."""

    institution_id: str
    id: NotRequired[str]
    created: NotRequired[str]
    max_historical_days: NotRequired[int]
    access_valid_for_days: NotRequired[int]
    access_scope: NotRequired[list[str]]
    accepted: NotRequired[str | None]
    reconfirmation: NotRequired[bool]


# ---------------------------------------------------------------------------
# Institutions  (GET /institutions/)
# ---------------------------------------------------------------------------


class GCInstitution(TypedDict):
    """A bank / financial institution."""

    id: str
    name: str
    logo: str
    countries: list[str]
    bic: NotRequired[str]
    transaction_total_days: NotRequired[str]
    max_access_valid_for_days: NotRequired[str]


# ---------------------------------------------------------------------------
# Requisitions  (POST /requisitions/ and GET /requisitions/{id}/)
# ---------------------------------------------------------------------------


class GCRequisition(TypedDict):
    """A GoCardless bank-linking requisition."""

    id: str
    institution_id: str
    redirect: str
    status: NotRequired[str]
    accounts: NotRequired[list[str]]
    link: NotRequired[str]
    reference: NotRequired[str]
    agreement: NotRequired[str]


# ---------------------------------------------------------------------------
# Account details  (GET /accounts/{id}/details/)
# ---------------------------------------------------------------------------


class GCAccountDetail(TypedDict):
    """The nested 'account' object inside an account-details response."""

    iban: NotRequired[str]
    bban: NotRequired[str]
    currency: NotRequired[str]
    ownerName: NotRequired[str]
    name: NotRequired[str]
    displayName: NotRequired[str]
    product: NotRequired[str]
    resourceId: NotRequired[str]
    bic: NotRequired[str]
    status: NotRequired[str]


class GCAccountDetailResponse(TypedDict):
    """Top-level response from GET /accounts/{id}/details/."""

    account: GCAccountDetail


# ---------------------------------------------------------------------------
# Account balances  (GET /accounts/{id}/balances/)
# ---------------------------------------------------------------------------


class GCBalance(TypedDict):
    """A single balance entry."""

    balanceAmount: GCAmount
    balanceType: str
    referenceDate: NotRequired[str]
    lastChangeDateTime: NotRequired[str]
    creditLimitIncluded: NotRequired[bool]
    lastCommittedTransaction: NotRequired[str]


class GCAccountBalances(TypedDict):
    """Top-level response from GET /accounts/{id}/balances/."""

    balances: list[GCBalance]


# ---------------------------------------------------------------------------
# Account transactions  (GET /accounts/{id}/transactions/)
# ---------------------------------------------------------------------------


class GCTransaction(TypedDict):
    """A single booked or pending bank transaction."""

    transactionAmount: GCAmount
    transactionId: NotRequired[str]
    internalTransactionId: NotRequired[str]
    entryReference: NotRequired[str]
    bookingDate: NotRequired[str]
    valueDate: NotRequired[str]
    bookingDateTime: NotRequired[str]
    creditorName: NotRequired[str]
    debtorName: NotRequired[str]
    remittanceInformationUnstructured: NotRequired[str]
    remittanceInformationUnstructuredArray: NotRequired[list[str]]
    additionalInformation: NotRequired[str]
    bankTransactionCode: NotRequired[str]
    proprietaryBankTransactionCode: NotRequired[str]


class GCBankTransactions(TypedDict):
    """The 'transactions' object containing booked and pending lists."""

    booked: list[GCTransaction]
    pending: NotRequired[list[GCTransaction]]


class GCAccountTransactions(TypedDict):
    """Top-level response from GET /accounts/{id}/transactions/."""

    transactions: GCBankTransactions
    last_updated: NotRequired[str]
