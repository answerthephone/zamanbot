import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
import asyncio
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text
from db import engine

pd.options.display.float_format = '{:,.2f}'.format


def convert_to_kzt(amount, currency, rates_from_eur):
    eur_to_kzt = rates_from_eur["kzt"]
    if currency == "KZT":
        return amount
    if currency == "EUR":
        return amount * eur_to_kzt
    if currency.lower() in rates_from_eur:
        eur_to_currency = rates_from_eur[currency.lower()]
        currency_to_eur = 1 / eur_to_currency
        amount_in_eur = amount * currency_to_eur
        return amount_in_eur * eur_to_kzt
    raise ValueError(f"Неизвестная валюта: {currency}")


def plot_to_bytesio(fig) -> io.BytesIO:
    """Saves Matplotlib figure to BytesIO (PNG)"""
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", dpi=150)
    buffer.seek(0)
    plt.close(fig)
    return buffer

def get_user_financial_summary(user_id: int, last_n_days: int = 30) -> dict:
    # --- Load currency rates ---
    url = "https://latest.currency-api.pages.dev/v1/currencies/eur.json"
    response = requests.get(url)
    rates_from_eur = response.json()["eur"]

    # --- Load transactions ---
    df = pd.read_sql("SELECT * FROM transactions", engine)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # --- Filter by last_n_days ---
    cutoff_date = datetime.now() - timedelta(days=last_n_days)
    df = df[df["date"] >= cutoff_date]

    if df.empty:
        return {
            "user_id": user_id,
            "income": 0.0,
            "expense": 0.0,
            "net_balance": 0.0,
            "top_expense_categories": [],
            "recommendations": ["Нет данных за последние дни."],
            "graphs": {}
        }

    # --- Currency normalization ---
    df["amount_kzt"] = df.apply(
        lambda row: convert_to_kzt(row["amount"], row["currency"], rates_from_eur),
        axis=1
    )

    # --- Aggregations ---
    income_df = (
        df.groupby("user_id")["amount_kzt"]
        .sum()
        .reset_index()
        .rename(columns={"amount_kzt": "income"})
    )

    expense_df = (
        df.groupby("from_account_id")["amount_kzt"]
        .sum()
        .reset_index()
        .rename(columns={"from_account_id": "user_id", "amount_kzt": "expense"})
    )

    summary = pd.merge(income_df, expense_df, on="user_id", how="outer").fillna(0)
    summary["net_balance"] = summary["income"] - summary["expense"]

    if user_id not in summary["user_id"].values:
        return None

    user_row = summary[summary["user_id"] == user_id].iloc[0]
    user_income = user_row["income"]
    user_expense = user_row["expense"]
    user_balance = user_row["net_balance"]

    # --- Expenses by category ---
    user_expenses_df = df[df["from_account_id"] == user_id]
    user_expenses_by_category = (
        user_expenses_df.groupby("category")["amount_kzt"]
        .sum()
        .sort_values(ascending=False)
    )

    top_categories = []
    recommendations = []

    if not user_expenses_by_category.empty:
        for category, amount in user_expenses_by_category.head(5).items():
            top_categories.append({"category": category, "amount_kzt": round(amount, 2)})

        avg_expense = user_expenses_by_category.mean()
        for category, amount in user_expenses_by_category.head(3).items():
            if amount > avg_expense:
                recommendations.append(
                    f"Сократите расходы в категории {category} (потрачено {amount:,.0f} ₸)"
                )

        if user_balance < 0:
            recommendations.append("У вас отрицательный баланс, стоит пересмотреть траты или увеличить доход.")
    else:
        recommendations.append("Отличная финансовая стабильность — нет трат за этот период.")

    # --- GRAPHS ---
    sns.set(style="whitegrid")
    graphs = {}

    # Pie chart
    if not user_expenses_by_category.empty:
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.pie(
            user_expenses_by_category,
            labels=user_expenses_by_category.index,
            autopct="%1.1f%%",
            startangle=140
        )
        ax.set_title("Структура расходов по категориям")
        graphs["pie_chart"] = plot_to_bytesio(fig)

    # Line chart
    daily_expenses = (
        user_expenses_df.groupby(user_expenses_df["date"].dt.date)["amount_kzt"]
        .sum()
        .reset_index()
    )

    if not daily_expenses.empty:
        fig, ax = plt.subplots(figsize=(7, 4))
        sns.lineplot(data=daily_expenses, x="date", y="amount_kzt", marker="o", ax=ax)
        ax.set_title(f"Траты по дням (последние {last_n_days} дней)")
        ax.set_xlabel("Дата")
        ax.set_ylabel("Сумма (₸)")
        plt.xticks(rotation=45)
        graphs["line_chart"] = plot_to_bytesio(fig)

    # --- Final summary ---
    result = {
        "user_id": int(user_id),
        "income": round(user_income, 2),
        "expense": round(user_expense, 2),
        "net_balance": round(user_balance, 2),
        "top_expense_categories": top_categories,
        "recommendations": recommendations,
        "graphs": graphs
    }

    return result
