# analytics.py
import requests
import pandas as pd
import json

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

def user_financial_summary(csv_path, user_id):
    df = pd.read_csv(csv_path)
    url = "https://latest.currency-api.pages.dev/v1/currencies/eur.json"
    response = requests.get(url)
    rates_from_eur = response.json()["eur"]

    df["amount_kzt"] = df.apply(
        lambda row: convert_to_kzt(row["amount"], row["currency"], rates_from_eur),
        axis=1
    )

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
                recommendations.append(f"Сократите расходы в категории {category} (потрачено {amount:,.0f} ₸)")
        if user_balance < 0:
            recommendations.append("У вас отрицательный баланс, стоит пересмотреть траты или увеличить доход.")
    else:
        recommendations.append("Отличная финансовая стабильность — нет трат.")

    result = {
        "user_id": int(user_id),
        "income": round(user_income, 2),
        "expense": round(user_expense, 2),
        "net_balance": round(user_balance, 2),
        "top_expense_categories": top_categories,
        "recommendations": recommendations
    }

    return result


# Обертка для вызова через LLM
def get_user_financial_summary(user_id: int, csv_path: str = "data/transactions.csv"):
    return user_financial_summary(csv_path, user_id)
