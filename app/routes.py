from app import app # second app is the variable defined in app\__init__.py
import sqlite3
from flask import render_template
import pandas as pd

@app.route('/')
def index():
    # retrieve categories from database
    con = sqlite3.connect("data.sqlite3")
    categories_df = pd.read_sql_query("SELECT * FROM Categories", con)
    transactions_df = pd.read_sql_query("SELECT * FROM Transactions", con)
    con.close()

    # change type of booking_date to datetime and sort by it descending
    transactions_df.booking_date = pd.to_datetime(transactions_df.booking_date)
    transactions_df.sort_values(by="booking_date", ascending=False, inplace=True)

    # extract the transaction' month in a new column using datetime
    transactions_df["month"] = pd.to_datetime(transactions_df.booking_date).dt.strftime("%B %Y")

    # render html
    return render_template("index.html", categories_df=categories_df, transactions_df=transactions_df)
