from webapp import app #  variable app
import sqlite3
from flask import render_template
import pandas as pd
import plotly.express as px

@app.route('/')
@app.route('/overview')
def index():
    # retrieve categories from database
    # ParentCategories is used as an alias for Categories to avoid confusion in the second left join
    con = sqlite3.connect("data.sqlite3")
    transactions_table_query = """
        SELECT 
            Transactions.booking_date as booking_date,
            Transactions.desc as desc,
            Transactions.amount as amount,
            Transactions.currency as currency,
            Categories.name as category,
            ParentCategories.name as parent_category,
            Categories.type as type
        FROM
            Transactions
        LEFT JOIN
            Categories
        ON
            Transactions.category = Categories.cat_id
        LEFT JOIN
            Categories as ParentCategories
        ON
            Categories.parent_id = ParentCategories.cat_id
    """
    transactions_df = pd.read_sql_query(transactions_table_query, con)
    con.close()

    # change type of booking_date to datetime and sort by it descending
    transactions_df.booking_date = pd.to_datetime(transactions_df.booking_date)
    transactions_df.sort_values(by="booking_date", ascending=False, inplace=True)

    # extract the transaction' month in a new column using datetime
    transactions_df["month"] = transactions_df["booking_date"].dt.strftime('%B %Y')

    summary_df = transactions_df.groupby(by=["month", "type"])["amount"].sum().reset_index()
    summary_df = summary_df.fillna(0)

    # Sort the summary DataFrame by date
    summary_df["month"] = pd.to_datetime(summary_df["month"], format="%B %Y")
    summary_df = summary_df.sort_values("month", ascending=True)
    summary_df["month"] = summary_df["month"].dt.strftime('%B %Y')

    # show sums in absolute value
    summary_df["amount"] = summary_df["amount"].abs()

    # create bar chart of monthly expenses and incomes
    transactions_fig = px.bar(summary_df, x="month", y="amount", color="type", barmode="group")
    transactions_chart_html = transactions_fig.to_html(include_plotlyjs='cdn')

    # create pie chart of expenses by category
    categories_df = transactions_df[transactions_df["type"] == "Expense"].groupby(by=["parent_category"])["amount"].sum().reset_index()
    # keep negative values only and in absolute value
    categories_df = categories_df[categories_df["amount"] < 0]
    categories_df["amount"] = categories_df["amount"].abs()
    # create chart
    categories_fig = px.pie(categories_df, values="amount", names="parent_category")
    categories_chart_html = categories_fig.to_html(include_plotlyjs='cdn')

    # render html
    return render_template("overview.html", transactions_df=transactions_df, 
                           transactions_chart=transactions_chart_html, 
                           categories_chart=categories_chart_html)

@app.route('/transactions')
def transactions():
    # retrieve categories from database
    con = sqlite3.connect("data.sqlite3")
    transactions_table_query = """
        SELECT 
            Transactions.booking_date as booking_date,
            Transactions.desc as desc,
            Transactions.amount as amount,
            Transactions.currency as currency,
            Categories.name as category,
            Categories.type as type
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

    # render html
    return render_template("transactions.html", transactions_df=transactions_df)
