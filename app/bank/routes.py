from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends

from app.bank import linking, sync
from app.bank.client import GoCardlessBankDataClient, get_bank_client
from app.bank.schemas import (
    BankLinkOut,
    CompleteLinkIn,
    Country,
    Institution,
    LinkAccount,
    StartLinkIn,
    StartLinkOut,
    SyncResultOut,
)
from app.db import DbSession

router = APIRouter(prefix="/api/bank", tags=["bank"])

BankClient = Annotated[GoCardlessBankDataClient, Depends(get_bank_client)]


@router.get("/countries")
def get_countries() -> list[Country]:
    return list(linking.SUPPORTED_COUNTRIES)


@router.get("/institutions")
def get_institutions(client: BankClient, country: str) -> list[Institution]:
    return linking.get_institutions(client, country)


@router.post("/links")
def start_link(db: DbSession, client: BankClient, body: StartLinkIn) -> StartLinkOut:
    link = linking.start_link(
        db, client, body.institution_id, body.country_code, str(body.redirect_url)
    )
    return StartLinkOut(link=link)


@router.get("/links")
def get_links(db: DbSession) -> list[BankLinkOut]:
    now = datetime.now(UTC)
    return [
        BankLinkOut.from_model(link, linking.consent_status(link.expires_at, now))
        for link in linking.list_links(db)
    ]


@router.get("/links/{reference}/accounts")
def get_link_accounts(
    db: DbSession, client: BankClient, reference: str
) -> list[LinkAccount]:
    return linking.list_link_accounts(db, client, reference)


@router.post("/links/{reference}/complete", status_code=204)
def complete_link(
    db: DbSession, client: BankClient, reference: str, body: CompleteLinkIn
) -> None:
    linking.complete_link(db, client, reference, body.external_ids)


@router.post("/sync")
def sync_accounts(db: DbSession, client: BankClient) -> list[SyncResultOut]:
    return [
        SyncResultOut(
            account_id=result.account.id,
            account_name=result.account.name,
            new_transactions=result.new_transactions,
            error=result.error,
        )
        for result in sync.sync_all(db, client)
    ]
