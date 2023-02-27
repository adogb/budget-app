import pandas as pd
import config
import requests
import re

# extract transactions from each account a load into dataframe
# for account in accounts:
headers = {
    'accept': 'application/json',
    'Authorization': 'Bearer '+config.access_token,
}

response = requests.get('https://ob.nordigen.com/api/v2/accounts/'+config.accounts_ids["grundkto"]+'/transactions/?date_from=2023-01-01&date_to=2023-02-20', headers=headers)

response_dict = response.json()
df = pd.json_normalize(response_dict["transactions"]["booked"])

# transform
df = df[["transactionId","bookingDate","remittanceInformationUnstructured",\
  "transactionAmount.amount","transactionAmount.currency","additionalInformation"]]

df.rename(columns={"additionalInformation":"transac_type", "bookingDate":"booking_date", "remittanceInformationUnstructured":"desc_unstructured", "transactionAmount.amount":"amount", "transactionAmount.currency":"currency", "transactionId":"id"}, inplace=True)

df.desc_unstructured = df.desc_unstructured.str.split().str.join(" ")

def extract_relevant(row):
  if row.transac_type == "DANKORT-NOTA":
    return row.desc_unstructured.replace("Dankort-nota ", "", 1)
  elif (row.transac_type == "VISA KØB") | (row.transac_type == "VISA MODPOSTERING"):
    return re.search("\d+,\d\d (.+ Den \d\d\.\d\d)", row.desc_unstructured).group(1)
  elif row.transac_type == "BGS":
    return row.desc_unstructured.replace("Bgs ", "", 1)
  elif row.transac_type == "MOBILEPAY":
    return row.desc_unstructured.replace("MobilePay ", "", 1)
  else:
    return row.desc_unstructured

df["desc"] = df.apply(extract_relevant, axis=1)
# load into database