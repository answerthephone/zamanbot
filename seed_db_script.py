#!/usr/bin/env python3
from __future__ import annotations
import asyncio, os, random, uuid, argparse
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from dateutil.relativedelta import relativedelta

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from faker import Faker

from db import engine
from db.models import (
    t_users, t_accounts, t_financial_goals,
    t_loans, t_transactions
)

# ---------------- Config ----------------
FAKER_LOCALE = os.getenv("FAKER_LOCALE", "en_US")

N_USERS        = int(os.getenv("SEED_N_USERS", "100"))
N_ACCOUNTS     = int(os.getenv("SEED_N_ACCOUNTS", "200"))
N_TRANSACTIONS = int(os.getenv("SEED_N_TRANSACTIONS", "3000"))
N_GOALS        = int(os.getenv("SEED_N_GOALS", "150"))
N_LOANS        = int(os.getenv("SEED_N_LOANS", "50"))
BATCH_SIZE     = int(os.getenv("SEED_BATCH_SIZE", "1000"))

fake = Faker(FAKER_LOCALE)
Faker.seed(42)
random.seed(42)

ACCOUNT_TYPES = ["business_card", "deposit_vygodniy", "deposit_overnight"]
CURRENCIES    = ["KZT", "USD", "RUB", "EUR", "CNY"]

CITIES       = ["Almaty","Astana","Shymkent","Karaganda","Aktobe","Pavlodar","Kostanay","Atyrau"]
CITY_WEIGHTS = [20, 20, 10, 5, 5, 5, 5, 5]
SEXES        = ["male", "female"]

PRIORITIES = ["low", "medium", "high"]
GOAL_ACTIONS = ["Buy","Save for","Plan for","Fund","Prepare for","Set aside for"]
GOAL_TARGETS = ["car","apartment","laptop","vacation","wedding","education","retirement",
                "emergency","new phone","business","furniture","bicycle","camera","home repair",
                "medical expenses","birthday gift","study abroad","gaming PC","future child","pet"]
LOAN_PURPOSES = [
  "Buy an apartment","Home renovation","Build a house","Mortgage refinancing","Buy a car","Repair a car",
  "Motorcycle purchase","Pay for education","Study abroad","Professional courses","Travel expenses",
  "Wedding","Medical treatment","Home appliances","Furniture","Start a small business",
  "Purchase of equipment","Working capital"
]
LOAN_TYPES = ["secured","unsecured"]

TX_CATEGORIES = ["groceries","restaurants","transport","online_shopping","entertainment","utilities","clothes","recurring","transfer"]
RECEIVER_CATALOG = {
  "groceries":[("Magnum",["milk","bread","apples","chicken","rice"]),
               ("SmallMart",["juice","cookies","cheese","eggs","pasta"]),
               ("GreenMart",["vegetables","fruits","olive oil","yogurt"])],
  "restaurants":[("BurgerTime",["burger","fries","cola"]),
                 ("CoffeeGo",["latte","cappuccino","croissant"]),
                 ("Sakura Sushi",["sushi set","ramen","miso soup"])],
  "transport":[("Yandex Go",["taxi ride"]),
               ("Kaspi Red Transport",["bus ticket"]),
               ("AirAstana",["plane ticket"])],
  "online_shopping":[("Wildberries",["clothes","sneakers","headphones"]),
                     ("Kaspi.kz",["smartphone","laptop","TV"]),
                     ("AliExpress",["phone case","LED strip","keyboard"])],
  "entertainment":[("Netflix",["monthly subscription"]),
                   ("Steam",["game purchase"]),
                   ("Spotify",["premium subscription"])],
  "utilities":[("KEGOC",["electricity bill"]),
               ("KazWater",["water bill"]),
               ("Beeline",["mobile plan"])],
  "clothes":[("Zara",["shirt","coat","trousers","belt"]),
             ("H&M",["t-shirt","hoodie","shorts"]),
             ("LC Waikiki",["scarf","hat","boots"])],
  "recurring":[("Netflix",["monthly subscription"]),
               ("Spotify",["music subscription"]),
               ("YouTube Premium",["monthly subscription"]),
               ("Kaspi Insurance",["car insurance"]),
               ("Beeline",["mobile plan"]),
               ("KazakhTelecom",["home internet"]),
               ("GymPro",["gym membership"]),
               ("Magnum",["monthly grocery delivery"]),
               ("Kaspi Red",["loan payment"]),
               ("KEGOC",["electricity bill"])]
}

# ---------------- Helpers ----------------
def d2(x) -> Decimal:
    return Decimal(f"{float(x):.2f}")

def tznow() -> datetime:
    return datetime.now(timezone.utc)

def random_birthdate(min_age=18, max_age=90) -> date:
    today = date.today()
    return fake.date_between(date(today.year-max_age,1,1), date(today.year-min_age,12,31))

def money_range(curr: str, lo: float, hi: float) -> Decimal:
    return d2(random.uniform(lo, hi))

def goal_target(curr: str) -> Decimal:
    return {
        "KZT": money_range(curr, 500_000, 10_000_000),
        "USD": money_range(curr, 1_000, 50_000),
        "EUR": money_range(curr, 1_000, 40_000),
        "RUB": money_range(curr, 50_000, 3_000_000),
        "CNY": money_range(curr, 10_000, 300_000),
    }[curr]

def loan_amount(curr: str) -> Decimal:
    if curr != "KZT": raise ValueError(curr)
    return money_range(curr, 100_000, 10_000_000)

def tx_amount(curr: str) -> Decimal:
    return {
      "KZT": money_range(curr, 500, 500_000),
      "USD": money_range(curr, 5, 5_000),
      "EUR": money_range(curr, 5, 4_000),
      "RUB": money_range(curr, 100, 300_000),
      "CNY": money_range(curr, 50, 30_000),
    }[curr]

def tx_details(cat: str):
    if cat == "transfer":
        return None, None
    receiver, items = random.choice(RECEIVER_CATALOG[cat])
    return receiver, random.choice(items)

def chunked(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]


# ---------------- Generators ----------------
def gen_users(n):
    rows = []
    for i in range(n):
        rows.append({
            "id": i + 1,  # INT PRIMARY KEY
            "name": fake.name(),
            "email": fake.unique.email(),
            "sex": random.choice(SEXES),
            "birth_date": random_birthdate(),
            "city": random.choices(CITIES, weights=CITY_WEIGHTS)[0],
        })
    return rows

def gen_accounts(n, user_ids):
    rows = []
    for _ in range(n):
        acc_type = random.choice(ACCOUNT_TYPES)
        currency = random.choice(CURRENCIES)
        opened = fake.date_between(start_date="-3y", end_date="today")

        if currency == "KZT": balance = money_range(currency, 10_000, 5_000_000)
        elif currency == "USD": balance = money_range(currency, 100, 20_000)
        elif currency == "EUR": balance = money_range(currency, 100, 15_000)
        elif currency == "RUB": balance = money_range(currency, 1_000, 1_000_000)
        elif currency == "CNY": balance = money_range(currency, 500, 100_000)
        else: raise RuntimeError

        if acc_type == "business_card":
            rate, ends = None, None
        else:
            months = random.randint(3, 12) if acc_type == "deposit_vygodniy" else random.randint(1, 12)
            rate = d2(17 if acc_type == "deposit_vygodniy" else 12)
            ends = opened + relativedelta(months=months)

        rows.append({
            "id": uuid.uuid4(),
            "user_id": random.choice(user_ids),  # INTEGER FK
            "type": acc_type,
            "balance": balance,
            "currency": currency,
            "interest_rate": rate,
            "opened_at": opened,
            "ends_at": ends,
        })
    return rows

def gen_goals(n, user_ids, account_ids):
    rows = []
    for _ in range(n):
        created = fake.date_between(start_date="-1y", end_date="today")
        deadline = (datetime.combine(created, datetime.min.time()) + timedelta(days=random.randint(90, 720))).date()
        currency = random.choice(CURRENCIES)
        target = goal_target(currency)
        current = d2(random.uniform(0, float(target) * 0.97))
        rows.append({
            "id": uuid.uuid4(),
            "user_id": random.choice(user_ids),
            "account_id": random.choice(account_ids),
            "name": f"{random.choice(GOAL_ACTIONS)} {random.choice(GOAL_TARGETS)}",
            "target_amount": target,
            "current_amount": current,
            "currency": currency,
            "deadline": deadline,
            "priority": random.choice(PRIORITIES),
        })
    return rows

def gen_loans(n, user_ids, account_ids):
    rows = []
    for _ in range(n):
        n_months = random.randint(3, 60)
        issued_date = fake.date_between(start_date="-3y", end_date="-1m")
        rows.append({
            "id": uuid.uuid4(),
            "user_id": random.choice(user_ids),
            "account_id": random.choice(account_ids),
            "loan_type": random.choice(LOAN_TYPES),
            "amount": loan_amount("KZT"),
            "currency": "KZT",
            "issued_date": issued_date,
            "end_date": issued_date + relativedelta(months=n_months),
            "n_months": n_months,
            "status": "overdue" if random.random() < 0.10 else "active",
            "purpose": random.choice(LOAN_PURPOSES),
        })
    return rows

def gen_transactions(n, user_ids, account_ids):
    rows = []
    for _ in range(n):
        currency = random.choice(CURRENCIES)
        cat = random.choice(TX_CATEGORIES)
        receiver, desc = tx_details(cat)
        rows.append({
            "id": uuid.uuid4(),
            "user_id": random.choice(user_ids),
            "from_account_id": random.choice(account_ids),
            "datetime": fake.date_time_between(start_date="-6m", end_date="now", tzinfo=timezone.utc),
            "amount": tx_amount(currency),
            "currency": currency,
            "category": cat,
            "receiver": receiver,
            "description": desc,
        })
    return rows


# ---------------- Async helpers ----------------
async def table_count(conn: sa.ext.asyncio.AsyncConnection, table: sa.Table) -> int:
    res = await conn.execute(sa.select(sa.func.count()).select_from(table))
    return int(res.scalar_one())

async def bulk_insert(conn, table, rows, label, batch=BATCH_SIZE):
    if not rows:
        return
    for chunk in chunked(rows, batch):
        await conn.execute(sa.insert(table), chunk)
    print(f"Inserted {len(rows):>6} into {label}")

async def truncate_all(conn):
    for name in ["transactions","loans","financial_goals","accounts","users"]:
        await conn.execute(text(f'TRUNCATE TABLE "public"."{name}" CASCADE;'))
    print("Truncated tables.")


# ---------------- Main ----------------
async def main():
    parser = argparse.ArgumentParser(description="Async DB seeder")
    parser.add_argument("--force", action="store_true", help="Truncate and reseed")
    args = parser.parse_args()

    async with engine.begin() as conn:
        if args.force:
            await truncate_all(conn)
        else:
            if await table_count(conn, t_users) > 0:
                print("Data already present. Use --force to reseed.")
                return

        users_rows = gen_users(N_USERS)
        user_ids   = [r["id"] for r in users_rows]
        accounts_rows = gen_accounts(N_ACCOUNTS, user_ids)
        account_ids   = [r["id"] for r in accounts_rows]
        goals_rows = gen_goals(N_GOALS, user_ids, account_ids)
        loans_rows = gen_loans(N_LOANS, user_ids, account_ids)
        tx_rows    = gen_transactions(N_TRANSACTIONS, user_ids, account_ids)

        await bulk_insert(conn, t_users, users_rows, "public.users")
        await bulk_insert(conn, t_accounts, accounts_rows, "public.accounts")
        await bulk_insert(conn, t_financial_goals, goals_rows, "public.financial_goals")
        await bulk_insert(conn, t_loans, loans_rows, "public.loans")
        await bulk_insert(conn, t_transactions, tx_rows, "public.transactions")

        print("Seeding complete.")

if __name__ == "__main__":
    asyncio.run(main())

