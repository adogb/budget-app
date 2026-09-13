"""
Custom exceptions for the service layer.
"""


class ServiceException(Exception):
    """Base exception for service layer errors."""


class SetupNotCompleteError(ServiceException):
    """Raised when bank setup hasn't been completed."""


class ConfigNotFoundError(ServiceException):
    """Raised when config file is missing."""


class BankAPIError(ServiceException):
    """Raised when bank API calls fail."""

    def __init__(self, message: str, account_id: str | None = None):
        self.account_id = account_id
        super().__init__(message)


class InvalidConfigError(ServiceException):
    """Raised when config file is malformed or invalid."""
