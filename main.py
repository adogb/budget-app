import pandas as pd
import config
import requests
import re
import sqlite3

# extract transactions from each account a load into dataframe
# for account in accounts:
headers = {
    'accept': 'application/json',
    'Authorization': 'Bearer '+config.access_token,
}

response = requests.get('https://ob.nordigen.com/api/v2/accounts/'+config.accounts_ids["grundkto"]+'/transactions/?date_from=2023-05-01&date_to=2023-05-08', headers=headers)

response_dict = response.json()
df = pd.json_normalize(response_dict["transactions"]["booked"])

# transform
df = df[["transactionId","bookingDate","remittanceInformationUnstructured",\
  "transactionAmount.amount","transactionAmount.currency","additionalInformation"]]

df.rename(columns={"additionalInformation":"trans_type", "bookingDate":"booking_date", "remittanceInformationUnstructured":"desc_unstructured", "transactionAmount.amount":"amount", "transactionAmount.currency":"currency", "transactionId":"id"}, inplace=True)

df.desc_unstructured = df.desc_unstructured.str.split().str.join(" ")

def extract_relevant(row):
  if row.trans_type == "DANKORT-NOTA":
    return row.desc_unstructured.replace("Dankort-nota ", "", 1)
  elif (row.trans_type == "VISA KØB") | (row.trans_type == "VISA MODPOSTERING"):
    return re.search("\d+,\d\d (.+ Den \d\d\.\d\d)", row.desc_unstructured).group(1)
  elif row.trans_type == "BGS":
    return row.desc_unstructured.replace("Bgs ", "", 1)
  elif row.trans_type == "MOBILEPAY":
    return row.desc_unstructured.replace("MobilePay ", "", 1)
  else:
    return row.desc_unstructured

df["desc"] = df.apply(extract_relevant, axis=1)
df = df[["id","booking_date","desc","desc_unstructured", "amount", "currency", "trans_type"]]

# Create database
""" con = sqlite3.connect("data.sqlite3") # returns a Connection Object. Extension is by choice, could be .db or .sqlite
cur = con.cursor() # returns a Cursor Object using the connection
cur.execute("CREATE TABLE Transactions (trans_id TEXT PRIMARY KEY, booking_date TEXT, desc TEXT, desc_original TEXT, amount REAL, currency TEXT, type TEXT) WITHOUT ROWID") # in reality, flexible typing from SQLite does not require specifying data types
cur.execute("CREATE TABLE Categories (cat_id INTEGER PRIMARY KEY, level INTEGER NOT NULL, parent_id INTEGER, name TEXT NOT NULL, desc TEXT, FOREIGN KEY(parent_id) REFERENCES Categories(cat_id))")
cur.execute("CREATE TABLE Keywords (keyword TEXT NOT NULL, category INTEGER, FOREIGN KEY(category) REFERENCES Categories(cat_id))")
con.commit()
con.close() """

# Building the database
con = sqlite3.connect("data.sqlite3")
cur = con.cursor()
cur.executemany("INSERT INTO Transactions VALUES(" + "?,"*(len(df.columns)-1) + "?)", df.to_numpy()) # SQLite uses ? as placeholder. Don't use string formatting to avoid SQL injection. df.to_numpy() gives a list of rows (themselves a list of values)

