"""
Custom exceptions for the service layer.
"""


class ServiceException(Exception):
    """Base exception for service layer errors."""


class BankAPIError(ServiceException):
    """Raised when bank API calls fail."""

    def __init__(self, message: str, account_id: str | None = None):
        self.account_id = account_id
        super().__init__(message)
