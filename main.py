import pandas as pd
import config
import requests

# extract transactions from each account a load into dataframe
# for account in accounts:
headers = {
    'accept': 'application/json',
    'Authorization': 'Bearer '+config.access_token,
}

response = requests.get('https://ob.nordigen.com/api/v2/accounts/'+config.accounts_ids["grundkto"]+'/transactions/?date_from=2023-01-01&date_to=2023-02-13', headers=headers)

response_dict = response.json()
df = pd.json_normalize(response_dict["transactions"]["booked"])

# transform
df = df[["transactionId","bookingDate","remittanceInformationUnstructured",\
  "transactionAmount.amount","transactionAmount.currency","additionalInformation"]]

df.rename(columns={"additionalInformation":"info", "bookingDate":"booking_date", "remittanceInformationUnstructured":"desc_unstructured", "transactionAmount.amount":"amount", "transactionAmount.currency":"currency", "transactionId":"id"}, inplace=True)

# load into database