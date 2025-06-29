from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import RedirectResponse, HTMLResponse
from app.services.gc_bank_data import GoCardlessBankDataClient
from app.dependencies import get_bank_client
import os
import json
from typing import List, Dict, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/setup", tags=["setup"])

# Simple file storage for our MVP (single user)
CONFIG_DIR = os.path.join(os.getcwd(), "config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "user_config.json")

# In-memory storage for setup process
# In a real app, this would use proper session management
setup_data = {}

class Institution(BaseModel):
    id: str
    name: str
    logo: str = ""
    countries: List[str] = []

class SetupStatusResponse(BaseModel):
    status: str
    accounts: Optional[List[Dict]] = None
    next_step: Optional[str] = None

class CountryResponse(BaseModel):
    code: str
    name: str

class AccountSelectionRequest(BaseModel):
    account_ids: List[str]

@router.get("/", response_model=SetupStatusResponse)
def check_setup_status():
    """Check if the initial setup has been completed"""
    if os.path.exists(CONFIG_FILE):
        try:
            # Load the configuration
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            
            # Return basic account info
            account_ids = config.get('selected_accounts', [])
            return {
                "status": "configured",
                "accounts": [{"id": account_id} for account_id in account_ids],
                "next_step": "/accounts"
            }
        except Exception:
            # If we can't read the config, consider it not configured
            return {"status": "not_configured", "next_step": "/setup/countries"}
    
    return {"status": "not_configured", "next_step": "/setup/countries"}

@router.get("/countries", response_model=Dict[str, List[CountryResponse]])
def get_countries():
    """Get list of supported countries"""
    # Hardcoded for simplicity - in a real app you might fetch this from the API
    return {
        "countries": [
            {"code": "GB", "name": "United Kingdom"},
            {"code": "DE", "name": "Germany"},
            {"code": "FR", "name": "France"},
            {"code": "ES", "name": "Spain"},
            {"code": "IT", "name": "Italy"},
            {"code": "NL", "name": "Netherlands"},
            {"code": "FI", "name": "Finland"},
            {"code": "NO", "name": "Norway"},
            {"code": "SE", "name": "Sweden"},
            {"code": "DK", "name": "Denmark"},
            {"code": "BE", "name": "Belgium"},
            {"code": "AT", "name": "Austria"},
        ]
    }

@router.get("/institutions/{country_code}")
def get_institutions(country_code: str, client: GoCardlessBankDataClient = Depends(get_bank_client)):
    """Get banks available for the selected country"""
    try:
        # Get institutions from GoCardless
        institutions = client.get_institutions(country_code)
        
        # Format the response for better usability
        formatted_institutions = []
        for institution in institutions:
            formatted_institutions.append({
                "id": institution.get("id", ""),
                "name": institution.get("name", ""),
                "logo": institution.get("logo", ""),
                "countries": institution.get("countries", [])
            })
        
        return {"institutions": formatted_institutions}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get institutions: {str(e)}")

@router.post("/start-bank-link/{institution_id}")
def start_bank_link(
    institution_id: str, 
    redirect_url: Optional[str] = Query(None),
    client: GoCardlessBankDataClient = Depends(get_bank_client)
):
    """Start the bank linking process - creates a requisition and returns link for authentication"""
    try:
        # Set the default redirect URL to our callback endpoint
        callback_url = redirect_url or "http://localhost:8000/setup/bank-callback"
        
        # Generate a requisition (bank connection request)
        requisition = client.create_requisition(
            redirect_url=callback_url,
            institution_id=institution_id
        )
        
        # Store requisition ID in memory (would use a session in a real app)
        requisition_id = requisition.get('id')
        setup_data['requisition_id'] = requisition_id
        setup_data['institution_id'] = institution_id
        
        # Return the link that the user should visit for bank authentication
        return {
            "link": requisition.get('link'),
            "requisition_id": requisition_id,
            "status": "pending",
            "next_step": "Follow the link to authenticate with your bank"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create bank link: {str(e)}")

@router.get("/bank-callback")
def bank_callback(request: Request, client: GoCardlessBankDataClient = Depends(get_bank_client)):
    """Handle callback after bank authentication"""
    try:
        # Get the requisition ID from our in-memory storage
        requisition_id = setup_data.get('requisition_id')
        if not requisition_id:
            raise HTTPException(status_code=400, detail="No active bank linking process found")
        
        # Get the requisition to see if it was successful
        requisition = client.get_requisition(requisition_id)
        
        # Check if the requisition has accounts
        accounts = requisition.get('accounts', [])
        if not accounts:
            return {
                "status": "pending", 
                "message": "Bank authentication in progress", 
                "next_step": "Try refreshing this page in a few seconds"
            }
        
        # Store the account IDs
        setup_data['accounts'] = accounts
        
        # Get details for each account
        account_details = []
        for account_id in accounts:
            try:
                details = client.get_account_details(account_id)
                balances = client.get_account_balances(account_id)
                
                # Get a friendly account name and current balance
                account_name = details.get('account', {}).get('name', 'Account')
                
                balance_info = {}
                for balance in balances.get('balances', []):
                    if balance.get('balanceType') == 'interimAvailable':
                        balance_info = {
                            'amount': balance.get('balanceAmount', {}).get('amount', '0'),
                            'currency': balance.get('balanceAmount', {}).get('currency', '')
                        }
                        break
                
                account_details.append({
                    'id': account_id,
                    'name': account_name,
                    'iban': details.get('account', {}).get('iban', ''),
                    'balance': balance_info.get('amount', '0'),
                    'currency': balance_info.get('currency', '')
                })
            except Exception as e:
                # Log the error but continue with other accounts
                print(f"Error fetching account {account_id}: {str(e)}")
        
        # Provide a simple HTML response if no accounts were found
        if not account_details:
            return HTMLResponse(content="""
                <html>
                    <head><title>Setup - No Accounts Found</title></head>
                    <body>
                        <h1>No accounts found</h1>
                        <p>We couldn't find any accounts in your bank. Please try again or choose a different bank.</p>
                        <a href="/setup">Back to Setup</a>
                    </body>
                </html>
            """)
        
        # Return the account details for the user to select from
        return {
            "status": "success",
            "accounts": account_details,
            "next_step": "POST to /setup/complete-setup with selected account IDs"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process bank callback: {str(e)}")

@router.post("/complete-setup")
def complete_setup(
    request: AccountSelectionRequest, 
    client: GoCardlessBankDataClient = Depends(get_bank_client)
):
    """Complete the setup by saving the selected accounts"""
    try:
        # Check if we have requisition data
        requisition_id = setup_data.get('requisition_id')
        if not requisition_id:
            raise HTTPException(status_code=400, detail="No active bank linking process found")
        
        # Get all available accounts
        all_accounts = setup_data.get('accounts', [])
        
        # Validate that selected accounts are from our requisition
        for account_id in request.account_ids:
            if account_id not in all_accounts:
                raise HTTPException(status_code=400, detail=f"Invalid account ID: {account_id}")
        
        # Ensure config directory exists
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
        
        # Get token data for persistence
        token_data = client.save_tokens_to_dict()
        
        # Create the config object
        config = {
            "tokens": token_data,
            "requisition_id": requisition_id,
            "institution_id": setup_data.get('institution_id', ''),
            "selected_accounts": request.account_ids
        }
        
        # Save the config to file
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Clear setup data
        setup_data.clear()
        
        return {
            "status": "success", 
            "message": "Setup completed successfully",
            "next_step": "/accounts"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to complete setup: {str(e)}")

@router.delete("/reset")
def reset_setup():
    """Reset the setup process by deleting the config file"""
    try:
        # Clear in-memory setup data
        setup_data.clear()
        
        # Remove the config file if it exists
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
            
        return {"status": "success", "message": "Setup reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset setup: {str(e)}")

@router.get("/simple-ui", response_class=HTMLResponse)
def get_simple_ui():
    """Provide a simple HTML UI for the setup process"""
    return HTMLResponse(content="""
        <html>
            <head>
                <title>Budget App Setup</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 0; padding: 20px; line-height: 1.6; }
                    .container { max-width: 800px; margin: 0 auto; padding: 20px; }
                    h1, h2 { color: #333; }
                    .step { margin-bottom: 30px; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                    select, button { padding: 10px; margin: 10px 0; }
                    button { background-color: #4CAF50; color: white; border: none; cursor: pointer; }
                    button:hover { background-color: #45a049; }
                    #accountList { margin-top: 20px; }
                    .account { border: 1px solid #eee; padding: 10px; margin-bottom: 10px; border-radius: 3px; }
                    .account.selected { background-color: #e7f7e7; border-color: #4CAF50; }
                    .hidden { display: none; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Budget App Setup</h1>
                    
                    <div id="setupStatus" class="step">
                        <h2>Step 1: Check Setup Status</h2>
                        <p>First, let's check if you've already set up your bank connection.</p>
                        <button id="checkStatus">Check Status</button>
                        <div id="statusResult"></div>
                    </div>
                    
                    <div id="countrySelection" class="step hidden">
                        <h2>Step 2: Select Your Country</h2>
                        <p>Choose the country where your bank is located:</p>
                        <select id="countrySelect">
                            <option value="">Select a country...</option>
                        </select>
                    </div>
                    
                    <div id="bankSelection" class="step hidden">
                        <h2>Step 3: Select Your Bank</h2>
                        <p>Choose your bank from the list:</p>
                        <select id="bankSelect">
                            <option value="">Select a bank...</option>
                        </select>
                        <button id="connectBank">Connect to Bank</button>
                    </div>
                    
                    <div id="accountSelection" class="step hidden">
                        <h2>Step 4: Select Accounts</h2>
                        <p>Select the accounts you want to use with Budget App:</p>
                        <div id="accountList"></div>
                        <button id="saveAccounts">Save Selected Accounts</button>
                    </div>
                    
                    <div id="setupComplete" class="step hidden">
                        <h2>Setup Complete!</h2>
                        <p>Your bank connection has been set up successfully.</p>
                        <button id="viewAccounts">View Your Accounts</button>
                        <button id="resetSetup">Reset Setup</button>
                    </div>
                </div>
                
                <script>
                    // DOM elements
                    const setupStatus = document.getElementById('setupStatus');
                    const countrySelection = document.getElementById('countrySelection');
                    const bankSelection = document.getElementById('bankSelection');
                    const accountSelection = document.getElementById('accountSelection');
                    const setupComplete = document.getElementById('setupComplete');
                    
                    // Buttons
                    const checkStatusBtn = document.getElementById('checkStatus');
                    const connectBankBtn = document.getElementById('connectBank');
                    const saveAccountsBtn = document.getElementById('saveAccounts');
                    const viewAccountsBtn = document.getElementById('viewAccounts');
                    const resetSetupBtn = document.getElementById('resetSetup');
                    
                    // Selects
                    const countrySelect = document.getElementById('countrySelect');
                    const bankSelect = document.getElementById('bankSelect');
                    
                    // Results
                    const statusResult = document.getElementById('statusResult');
                    const accountList = document.getElementById('accountList');
                    
                    // Selected accounts
                    let selectedAccounts = [];
                    
                    // Check setup status
                    checkStatusBtn.addEventListener('click', async () => {
                        const response = await fetch('/setup');
                        const data = await response.json();
                        
                        if (data.status === 'configured') {
                            statusResult.innerHTML = 'You have already set up your bank connection.';
                            setupStatus.classList.add('hidden');
                            setupComplete.classList.remove('hidden');
                        } else {
                            statusResult.innerHTML = 'You need to set up your bank connection.';
                            setupStatus.classList.add('hidden');
                            loadCountries();
                        }
                    });
                    
                    // Load countries
                    async function loadCountries() {
                        const response = await fetch('/setup/countries');
                        const data = await response.json();
                        
                        countrySelect.innerHTML = '<option value="">Select a country...</option>';
                        data.countries.forEach(country => {
                            const option = document.createElement('option');
                            option.value = country.code;
                            option.textContent = country.name;
                            countrySelect.appendChild(option);
                        });
                        
                        countrySelection.classList.remove('hidden');
                    }
                    
                    // When country is selected, load banks
                    countrySelect.addEventListener('change', async () => {
                        const countryCode = countrySelect.value;
                        if (!countryCode) return;
                        
                        const response = await fetch(`/setup/institutions/${countryCode}`);
                        const data = await response.json();
                        
                        bankSelect.innerHTML = '<option value="">Select a bank...</option>';
                        data.institutions.forEach(bank => {
                            const option = document.createElement('option');
                            option.value = bank.id;
                            option.textContent = bank.name;
                            bankSelect.appendChild(option);
                        });
                        
                        bankSelection.classList.remove('hidden');
                    });
                    
                    // Connect to bank
                    connectBankBtn.addEventListener('click', async () => {
                        const bankId = bankSelect.value;
                        if (!bankId) return;
                        
                        const response = await fetch(`/setup/start-bank-link/${bankId}`, {
                            method: 'POST'
                        });
                        const data = await response.json();
                        
                        // Open bank authentication in a new window
                        window.open(data.link, '_blank');
                        
                        // Wait for user to complete bank auth
                        alert('Please complete the authentication in the new window, then come back here to continue.');
                        
                        // Check for accounts after bank auth
                        checkForAccounts(data.requisition_id);
                    });
                    
                    // Check for accounts
                    async function checkForAccounts() {
                        try {
                            const response = await fetch('/setup/bank-callback');
                            const data = await response.json();
                            
                            if (data.status === 'pending') {
                                // Still waiting, check again in 3 seconds
                                setTimeout(checkForAccounts, 3000);
                                return;
                            }
                            
                            if (data.status === 'success') {
                                // Show account selection
                                accountList.innerHTML = '';
                                data.accounts.forEach(account => {
                                    const accountDiv = document.createElement('div');
                                    accountDiv.classList.add('account');
                                    accountDiv.innerHTML = `
                                        <input type="checkbox" id="${account.id}" value="${account.id}">
                                        <label for="${account.id}">
                                            <strong>${account.name}</strong><br>
                                            Balance: ${account.balance} ${account.currency}<br>
                                            IBAN: ${account.iban || 'N/A'}
                                        </label>
                                    `;
                                    accountList.appendChild(accountDiv);
                                    
                                    // Add click handler for selection
                                    const checkbox = accountDiv.querySelector('input');
                                    checkbox.addEventListener('change', () => {
                                        if (checkbox.checked) {
                                            accountDiv.classList.add('selected');
                                            selectedAccounts.push(account.id);
                                        } else {
                                            accountDiv.classList.remove('selected');
                                            selectedAccounts = selectedAccounts.filter(id => id !== account.id);
                                        }
                                    });
                                });
                                
                                bankSelection.classList.add('hidden');
                                accountSelection.classList.remove('hidden');
                            }
                        } catch (error) {
                            console.error('Error checking for accounts:', error);
                            alert('There was an error checking for accounts. Please try again.');
                        }
                    }
                    
                    // Save selected accounts
                    saveAccountsBtn.addEventListener('click', async () => {
                        if (selectedAccounts.length === 0) {
                            alert('Please select at least one account.');
                            return;
                        }
                        
                        try {
                            const response = await fetch('/setup/complete-setup', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    account_ids: selectedAccounts
                                })
                            });
                            
                            const data = await response.json();
                            if (data.status === 'success') {
                                accountSelection.classList.add('hidden');
                                setupComplete.classList.remove('hidden');
                            } else {
                                alert('There was an error saving your accounts. Please try again.');
                            }
                        } catch (error) {
                            console.error('Error saving accounts:', error);
                            alert('There was an error saving your accounts. Please try again.');
                        }
                    });
                    
                    // View accounts
                    viewAccountsBtn.addEventListener('click', () => {
                        window.location.href = '/accounts';
                    });
                    
                    // Reset setup
                    resetSetupBtn.addEventListener('click', async () => {
                        if (!confirm('Are you sure you want to reset your setup? This will delete your bank connection.')) {
                            return;
                        }
                        
                        try {
                            const response = await fetch('/setup/reset', {
                                method: 'DELETE'
                            });
                            
                            const data = await response.json();
                            if (data.status === 'success') {
                                alert('Setup has been reset successfully.');
                                window.location.reload();
                            } else {
                                alert('There was an error resetting your setup. Please try again.');
                            }
                        } catch (error) {
                            console.error('Error resetting setup:', error);
                            alert('There was an error resetting your setup. Please try again.');
                        }
                    });
                </script>
            </body>
        </html>
    """)
