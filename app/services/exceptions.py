"""
Custom exceptions for the service layer.
"""

from typing import Optional


class ServiceException(Exception):
    """Base exception for service layer errors."""

    pass


class SetupNotCompleteError(ServiceException):
    """Raised when bank setup hasn't been completed."""

    pass


class ConfigNotFoundError(ServiceException):
    """Raised when config file is missing."""

    pass


class BankAPIError(ServiceException):
    """Raised when bank API calls fail."""

    def __init__(self, message: str, account_id: Optional[str] = None):
        self.account_id = account_id
        super().__init__(message)


class InvalidConfigError(ServiceException):
    """Raised when config file is malformed or invalid."""

    pass
