import os
import time
from uuid import uuid4

import requests
from requests.auth import AuthBase

from app.clients.gc_bank_data_models import (
    GCAccountBalances,
    GCAccountDetailResponse,
    GCAccountTransactions,
    GCEndUserAgreement,
    GCInstitution,
    GCRequisition,
)

BASE_URL = "https://bankaccountdata.gocardless.com/api/v2"
SECRET_ID = os.getenv("NORDIGEN_SECRET_ID")
SECRET_KEY = os.getenv("NORDIGEN_SECRET_KEY")


class GoCardlessBankAuth(AuthBase):
    """Custom auth handler for GoCardless Bank API token authentication.
    This modifies the client request to include the Authorization header with the Bearer token.
    It checks if the token is valid and refreshes it if necessary."""

    def __init__(self, client):
        self.client = client

    def __call__(self, r):
        # Check if token is valid, refresh if needed
        self.client.ensure_valid_token()
        # Add the authorization header to the request
        r.headers["Authorization"] = f"Bearer {self.client.access_token}"
        return r


class GoCardlessBankDataClient:
    def __init__(
        self, secret_id=SECRET_ID, secret_key=SECRET_KEY, token_refresh_buffer=60
    ):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.access_token = None
        self.refresh_token = None
        self.token_expires = 0  # Absolute timestamp
        self.refresh_expires = 0  # Absolute timestamp
        self.token_refresh_buffer = token_refresh_buffer

        # Create a session for connection pooling and persistence
        self.session = requests.Session()
        self.session.headers.update({"accept": "application/json"})
        # Set our custom auth handler
        self.session.auth = GoCardlessBankAuth(self)

    def ensure_valid_token(self) -> None:
        """Ensure we have a valid access token, refreshing if necessary."""
        now = int(time.time())
        # Check if token is missing or will expire soon
        if not self.access_token or now >= (
            self.token_expires - self.token_refresh_buffer
        ):
            # If we have a valid refresh token, use it
            if self.refresh_token and now < self.refresh_expires:
                self.refresh_access_token()
            else:
                # Otherwise get a completely new token
                self.get_access_token()

    def get_access_token(self) -> str:
        url = f"{BASE_URL}/token/new/"

        # Don't use self.session here to avoid auth loop
        # Include proper headers for the API request
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        resp = requests.post(
            url,
            json={"secret_id": self.secret_id, "secret_key": self.secret_key},
            headers=headers,
        )

        # Print response details for debugging if there's an error
        if resp.status_code != 200:
            print(f"Token request failed: {resp.status_code} {resp.reason}")
            print(f"Response: {resp.text}")

        resp.raise_for_status()
        data = resp.json()

        # Store tokens
        self.access_token = data["access"]
        self.refresh_token = data["refresh"]

        # Convert durations to absolute timestamps
        now = int(time.time())
        self.token_expires = now + data.get("access_expires", 0)
        self.refresh_expires = now + data.get("refresh_expires", 0)

        return self.access_token

    def refresh_access_token(self) -> str:
        """Use the refresh token to get a new access token. If refresh token is expired, get a new one."""
        if not self.refresh_token:
            # No refresh token, get a new one
            return self.get_access_token()

        now = int(time.time())
        if now >= self.refresh_expires:
            # Refresh token expired, get a new one
            return self.get_access_token()

        url = f"{BASE_URL}/token/refresh/"

        # Don't use self.session here to avoid auth loop
        # Include proper headers for the API request
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        resp = requests.post(url, json={"refresh": self.refresh_token}, headers=headers)

        # Print response details for debugging if there's an error
        if resp.status_code != 200:
            print(f"Token refresh failed: {resp.status_code} {resp.reason}")
            print(f"Response: {resp.text}")

        if resp.status_code == 401:
            # Refresh token expired or invalid, get a new one
            return self.get_access_token()

        resp.raise_for_status()
        data = resp.json()
        self.access_token = data["access"]

        # Convert duration to absolute timestamp
        self.token_expires = now + data.get("access_expires", 0)

        return self.access_token

    def get_institutions(self, country_code: str) -> list[GCInstitution]:
        url = f"{BASE_URL}/institutions/?country={country_code.lower()}"
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.json()

    def create_agreement(
        self,
        institution_id: str,
        max_historical_days: int = 90,
        access_valid_for_days: int = 90,
        access_scope: list[str] | None = None,
    ) -> GCEndUserAgreement:
        if access_scope is None:
            access_scope = ["balances", "details", "transactions"]
        url = f"{BASE_URL}/agreements/enduser/"
        payload = {
            "institution_id": institution_id,
            "max_historical_days": max_historical_days,
            "access_valid_for_days": access_valid_for_days,
            "access_scope": access_scope,
        }
        resp = self.session.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()

    def create_requisition(
        self,
        redirect_url: str,
        institution_id: str,
        reference: str | None = None,
        agreement_id: str | None = None,
        user_language: str = "EN",
    ) -> GCRequisition:
        url = f"{BASE_URL}/requisitions/"
        payload = {
            "redirect": redirect_url,
            "institution_id": institution_id,
            "reference": reference or str(uuid4()),
            "user_language": user_language,
        }
        if agreement_id:
            payload["agreement"] = agreement_id
        resp = self.session.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()

    def get_requisition(self, requisition_id: str) -> GCRequisition:
        url = f"{BASE_URL}/requisitions/{requisition_id}/"
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.json()

    def get_account_details(self, account_id: str) -> GCAccountDetailResponse:
        url = f"{BASE_URL}/accounts/{account_id}/details/"
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.json()

    def get_account_balances(self, account_id: str) -> GCAccountBalances:
        url = f"{BASE_URL}/accounts/{account_id}/balances/"
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.json()

    def get_account_transactions(
        self, account_id: str, date_from: str | None = None, date_to: str | None = None
    ) -> GCAccountTransactions:
        """
        Get account transactions with optional date filtering.

        Args:
            account_id (str): The account ID to get transactions for
            date_from (str, optional): Filter transactions from this date (ISO format: YYYY-MM-DD)
            date_to (str, optional): Filter transactions to this date (ISO format: YYYY-MM-DD)

        Returns:
            dict: Transaction data including booked and pending transactions
        """
        url = f"{BASE_URL}/accounts/{account_id}/transactions/"
        params = {}

        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to

        resp = self.session.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def get_token_status(self):
        """
        Get the current status of the access and refresh tokens.

        Returns:
            dict: Token status information including expiry timestamps and remaining time
        """
        now = int(time.time())
        access_remaining = max(0, self.token_expires - now)
        refresh_remaining = max(0, self.refresh_expires - now)

        return {
            "has_access_token": self.access_token is not None,
            "has_refresh_token": self.refresh_token is not None,
            "access_expires_at": self.token_expires,
            "refresh_expires_at": self.refresh_expires,
            "access_expires_in_seconds": access_remaining,
            "refresh_expires_in_seconds": refresh_remaining,
            "current_time": now,
            "is_access_valid": self.access_token is not None
            and now < self.token_expires,
            "is_refresh_valid": self.refresh_token is not None
            and now < self.refresh_expires,
        }

    def close(self):
        """Close the session when done to free resources."""
        self.session.close()
