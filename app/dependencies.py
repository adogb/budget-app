from fastapi import Depends
from app.services.gc_bank_data import GoCardlessBankDataClient
import os
import json

# Path to the user configuration file
CONFIG_DIR = os.path.join(os.getcwd(), "config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "user_config.json")

# Global client instance
_client = None

def get_bank_client() -> GoCardlessBankDataClient:
    """
    Get the GoCardless bank client, loading saved tokens if available.
    For the MVP, we use a single global instance.
    """
    global _client
    
    # Initialize if not already done
    if _client is None:
        _client = GoCardlessBankDataClient()
        
        # Try to load saved tokens if configuration exists
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    if "tokens" in config:
                        _client.load_tokens_from_dict(config["tokens"])
            except Exception:
                # If we fail to load tokens, we'll just continue with a fresh client
                pass
    
    return _client
