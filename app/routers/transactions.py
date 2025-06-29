from fastapi import APIRouter, Depends, HTTPException, Query
from app.models.transaction import Transaction
from app.dependencies import get_bank_client
from app.services.gc_bank_data import GoCardlessBankDataClient
import os
import json
from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import date, datetime, timedelta

# Path to the user configuration file
CONFIG_DIR = os.path.join(os.getcwd(), "config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "user_config.json")

router = APIRouter(prefix="/transactions", tags=["transactions"])

class TransactionResponse(BaseModel):
    id: str
    account_id: str
    amount: float
    currency: str
    description: str
    booking_date: date
    value_date: Optional[date] = None
    category: Optional[str] = None

@router.get("/", response_model=List[TransactionResponse])
def list_transactions(
    account_id: Optional[str] = None,
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    client: GoCardlessBankDataClient = Depends(get_bank_client)
):
    """List transactions with optional filtering"""
    # Check if setup has been completed
    if not os.path.exists(CONFIG_FILE):
        raise HTTPException(status_code=400, detail="Bank setup not completed. Please visit /setup first.")
    
    try:
        # Load the configuration file
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        # Get the account IDs to query
        account_ids = []
        if account_id:
            # Specific account requested
            account_ids = [account_id]
        else:
            # All selected accounts
            account_ids = config.get('selected_accounts', [])
        
        if not account_ids:
            return []
        
        # Set default date range to the past month if not specified
        if not from_date:
            from_date = (datetime.now() - timedelta(days=30)).date()
        if not to_date:
            to_date = datetime.now().date()
        
        # Convert to strings for the API
        date_from = from_date.isoformat()
        date_to = to_date.isoformat()
        
        # Fetch transactions for each account
        all_transactions = []
        for acc_id in account_ids:
            try:
                # Get transactions for this account with date filtering
                transactions = client.get_account_transactions_paginated(
                    acc_id,
                    date_from=date_from,
                    date_to=date_to
                )
                
                # Process booked transactions (confirmed)
                for tx in transactions.get('transactions', {}).get('booked', []):
                    try:
                        # Extract transaction details
                        tx_id = tx.get('internalTransactionId', '')
                        booking_date_str = tx.get('bookingDate', '')
                        value_date_str = tx.get('valueDate', '')
                        
                        # Parse the amount and handle negative values
                        amount_str = tx.get('transactionAmount', {}).get('amount', '0')
                        currency = tx.get('transactionAmount', {}).get('currency', '')
                        
                        # Get transaction description
                        description = tx.get('remittanceInformationUnstructured', '')
                        if not description:
                            description = tx.get('additionalInformation', '')
                        
                        # Create transaction response
                        all_transactions.append(TransactionResponse(
                            id=tx_id,
                            account_id=acc_id,
                            amount=float(amount_str),
                            currency=currency,
                            description=description,
                            booking_date=datetime.strptime(booking_date_str, '%Y-%m-%d').date() if booking_date_str else None,
                            value_date=datetime.strptime(value_date_str, '%Y-%m-%d').date() if value_date_str else None,
                            category=None  # We'll implement categorization later
                        ))
                    except Exception as e:
                        # Log the error but continue with other transactions
                        print(f"Error processing transaction in account {acc_id}: {str(e)}")
            except Exception as e:
                # Log the error but continue with other accounts
                print(f"Error fetching transactions for account {acc_id}: {str(e)}")
        
        # Sort transactions by booking date (newest first)
        all_transactions.sort(key=lambda x: x.booking_date, reverse=True)
        
        return all_transactions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve transactions: {str(e)}")
