"""
Service for managing application configuration.

Centralizes all config file I/O operations.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from app.services.exceptions import (
    ConfigNotFoundError,
    InvalidConfigError,
    SetupNotCompleteError,
)


class ConfigService:
    """Service for managing user configuration."""

    def __init__(self, config_dir: str = None, config_file: str = None):
        """
        Initialize ConfigService.

        Args:
            config_dir: Directory for config files (defaults to ./config)
            config_file: Full path to config file (defaults to ./config/user_config.json)
        """
        self.config_dir = config_dir or os.path.join(os.getcwd(), "config")
        self.config_file = config_file or os.path.join(
            self.config_dir, "user_config.json"
        )

    def load_config(self) -> Dict:
        """
        Load configuration from file.

        Returns:
            Dict containing configuration data

        Raises:
            ConfigNotFoundError: If config file doesn't exist
            InvalidConfigError: If config file is malformed
        """
        if not os.path.exists(self.config_file):
            raise ConfigNotFoundError(f"Config file not found: {self.config_file}")

        try:
            with open(self.config_file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise InvalidConfigError(f"Config file is malformed: {str(e)}")
        except Exception as e:
            raise InvalidConfigError(f"Failed to read config file: {str(e)}")

    def save_config(self, config: Dict) -> None:
        """
        Save configuration to file.

        Args:
            config: Configuration dictionary to save

        Raises:
            InvalidConfigError: If config cannot be saved
        """
        try:
            # Create config directory if it doesn't exist
            os.makedirs(self.config_dir, exist_ok=True)

            # Write config to file
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            raise InvalidConfigError(f"Failed to save config: {str(e)}")

    def delete_config(self) -> None:
        """
        Delete the config file.

        Raises:
            InvalidConfigError: If config cannot be deleted
        """
        try:
            if os.path.exists(self.config_file):
                os.remove(self.config_file)
        except Exception as e:
            raise InvalidConfigError(f"Failed to delete config: {str(e)}")

    def config_exists(self) -> bool:
        """Check if config file exists."""
        return os.path.exists(self.config_file)

    def is_setup_complete(self) -> bool:
        """
        Check if initial setup has been completed.

        Returns:
            True if setup is complete, False otherwise
        """
        if not self.config_exists():
            return False

        try:
            config = self.load_config()
            return config.get("setup_complete", False)
        except (ConfigNotFoundError, InvalidConfigError):
            return False

    def require_setup_complete(self) -> None:
        """
        Raise an exception if setup is not complete.

        Raises:
            SetupNotCompleteError: If setup hasn't been completed
        """
        if not self.is_setup_complete():
            raise SetupNotCompleteError(
                "Bank setup not completed. Please complete setup first."
            )

    def get_selected_accounts(self) -> List[str]:
        """
        DEPRECATED: Use database queries instead.
        Get the list of selected account IDs from config.
        This is kept for backward compatibility but accounts should be queried from DB.

        Returns:
            List of account IDs

        Raises:
            SetupNotCompleteError: If setup hasn't been completed
        """
        self.require_setup_complete()
        config = self.load_config()
        return config.get("selected_accounts", [])

    def get_tokens(self) -> Optional[Dict]:
        """
        Get authentication tokens from config.

        Returns:
            Token dictionary or None if not found
        """
        if not self.config_exists():
            return None

        try:
            config = self.load_config()
            return config.get("tokens")
        except (ConfigNotFoundError, InvalidConfigError):
            return None

    def get_requisition_id(self) -> Optional[str]:
        """
        Get the requisition ID from config.

        Returns:
            Requisition ID or None if not found
        """
        if not self.config_exists():
            return None

        try:
            config = self.load_config()
            return config.get("requisition_id")
        except (ConfigNotFoundError, InvalidConfigError):
            return None

    def get_institution_id(self) -> Optional[str]:
        """
        Get the institution ID from config.

        Returns:
            Institution ID or None if not found
        """
        if not self.config_exists():
            return None

        try:
            config = self.load_config()
            return config.get("institution_id")
        except (ConfigNotFoundError, InvalidConfigError):
            return None

    def create_complete_config(
        self,
        tokens: Dict,
        requisition_id: str,
        institution_id: str,
        country_code: str = "GB",
    ) -> None:
        """
        Create a complete configuration after setup.
        Note: Accounts are stored in the database, not in config.

        Args:
            tokens: Authentication tokens
            requisition_id: GoCardless requisition ID
            institution_id: Bank institution ID
            country_code: Country code for the institution
        """
        config = {
            "tokens": tokens,
            "requisition_id": requisition_id,
            "institution_id": institution_id,
            "country_code": country_code,
            "setup_complete": True,
            "setup_date": datetime.now().isoformat(),
        }
        self.save_config(config)

    def get_country_code(self) -> Optional[str]:
        """
        Get the country code from config.

        Returns:
            Country code or None if not found
        """
        if not self.config_exists():
            return None

        try:
            config = self.load_config()
            return config.get("country_code")
        except (ConfigNotFoundError, InvalidConfigError):
            return None
