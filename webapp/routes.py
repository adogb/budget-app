from webapp import app #  variable app
import sqlite3
from flask import render_template
import pandas as pd
import plotly.express as px

@app.route('/')
def index():
    # retrieve categories from database
    con = sqlite3.connect("data.sqlite3")
    transactions_table_query = """
        SELECT 
            Transactions.booking_date as booking_date,
            Transactions.desc as desc,
            Transactions.amount as amount,
            Transactions.currency as currency,
            Categories.name as category
        FROM
            Transactions
        LEFT JOIN
            Categories
        ON
            Transactions.category = Categories.cat_id
    """
    transactions_df = pd.read_sql_query(transactions_table_query, con)
    con.close()

    # change type of booking_date to datetime and sort by it descending
    transactions_df.booking_date = pd.to_datetime(transactions_df.booking_date)
    transactions_df.sort_values(by="booking_date", ascending=False, inplace=True)

    # extract the transaction' month in a new column using datetime
    transactions_df["month"] = pd.to_datetime(transactions_df.booking_date, format="%B %Y")

    # create dataframe for bar chart
    expenses_df = transactions_df[transactions_df['category'] != 'Salary']
    incomes_df = transactions_df[transactions_df['category'] == 'Salary']

    expenses_grouped = expenses_df.groupby(by=transactions_df['month'].dt.strftime('%B %Y'))['amount'].sum().reset_index()
    incomes_grouped = incomes_df.groupby(by=transactions_df['month'].dt.strftime('%B %Y'))['amount'].sum().reset_index()

    # Merge the two DataFrames on the 'Date' column to create a summary DataFrame
    summary_df = expenses_grouped.merge(incomes_grouped, on='month', how='outer')
    summary_df.columns = ['month', 'expenses', 'incomes']

    # create bar chart of monthly expenses and incomes
    fig = px.bar(summary_df, x="month", y="expenses")
    graph_html = fig.to_html(include_plotlyjs='cdn')

    # render html
    return render_template("index.html", transactions_df=transactions_df, graph=graph_html)
