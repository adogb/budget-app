from typing import Self

from requests import RequestException


class BankAPIError(Exception):
    """A call to the bank data API failed."""

    @classmethod
    def from_request(cls, action: str, error: RequestException) -> Self:
        """E.g. "Could not fetch transactions: Rate limit exceeded (try tomorrow)"."""
        return cls(f"{action}: {_reason(error)}")


def _reason(error: RequestException) -> str:
    """GoCardless explains errors in `summary` and `detail`; prefer those."""
    if error.response is None:
        return str(error)
    try:
        body = error.response.json()
    except ValueError:
        return str(error)
    if not isinstance(body, dict) or not body.get("summary"):
        return str(error)
    detail = body.get("detail")
    return f"{body['summary']} ({detail})" if detail else str(body["summary"])
