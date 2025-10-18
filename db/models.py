import sqlalchemy as sa
from sqlalchemy import (
    Column, ForeignKey, MetaData, Table, CheckConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime

metadata = MetaData(schema="public")

# Common types
UUID_PK = Column("id", UUID(as_uuid=True), primary_key=True,
                 server_default=sa.text("gen_random_uuid()"))

MONEY = lambda: sa.Numeric(14, 2)
PERCENT = lambda: sa.Numeric(5, 2)  # e.g., 12.34 (%)
CURRENCY = lambda: sa.String(3)     # ISO code like 'USD', 'KZT'
TS = lambda: sa.TIMESTAMP(timezone=True)
DATE = lambda: sa.Date()
TEXT = lambda: sa.Text()
INT = lambda: sa.Integer()
BIGINT = lambda: sa.BigInteger()


# ---------- USERS ----------
t_users = Table(
    "users", metadata,
    UUID_PK,
    # keep old numeric id for import/mapping (optional but very useful)
    Column("legacy_id", sa.BigInteger(), nullable=True, unique=True),
    Column("name", TEXT(), nullable=False),
    Column("email", TEXT(), nullable=True, unique=True),
    Column("sex", TEXT(), nullable=True),            # could be Enum later
    Column("birth_date", DATE(), nullable=True),
    Column("city", TEXT(), nullable=True),
    Column("created_at", TS(), nullable=False, server_default=sa.text("now()")),
)

# ---------- ACCOUNTS ----------
t_accounts = Table(
    "accounts", metadata,
    UUID_PK,
    Column("legacy_id", sa.BigInteger(), nullable=True, unique=True),
    Column("user_id", UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("type", TEXT(), nullable=False),
    Column("balance", MONEY(), nullable=False, server_default="0"),
    Column("currency", CURRENCY(), nullable=False),
    Column("interest_rate", PERCENT(), nullable=True),  # percent value
    Column("opened_at", DATE(), nullable=True),
    Column("ends_at", DATE(), nullable=True),
    Column("created_at", TS(), nullable=False, server_default=sa.text("now()")),
    CheckConstraint("balance >= 0", name="ck_accounts_balance_nonneg"),
)

Index("ix_accounts_user_currency", t_accounts.c.user_id, t_accounts.c.currency)

# ---------- FINANCIAL GOALS ----------
t_financial_goals = Table(
    "financial_goals", metadata,
    UUID_PK,
    Column("legacy_id", sa.BigInteger(), nullable=True, unique=True),
    Column("user_id", UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("account_id", UUID(as_uuid=True), ForeignKey("public.accounts.id", ondelete="CASCADE"), nullable=True, index=True),
    Column("name", TEXT(), nullable=False),
    Column("target_amount", MONEY(), nullable=False),
    Column("current_amount", MONEY(), nullable=False, server_default="0"),
    Column("currency", CURRENCY(), nullable=False),
    Column("deadline", DATE(), nullable=True),
    Column("created_at", TS(), nullable=False, server_default=sa.text("now()")),
    Column("priority", TEXT(), nullable=True),  # optional Enum later
    CheckConstraint("current_amount >= 0", name="ck_goals_current_nonneg"),
    CheckConstraint("target_amount >= 0", name="ck_goals_target_nonneg"),
)

# ---------- LOANS ----------
t_loans = Table(
    "loans", metadata,
    UUID_PK,
    Column("legacy_id", sa.BigInteger(), nullable=True, unique=True),
    Column("user_id", UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("account_id", UUID(as_uuid=True), ForeignKey("public.accounts.id", ondelete="SET NULL"), nullable=True, index=True),
    Column("loan_type", TEXT(), nullable=True),
    Column("amount", MONEY(), nullable=False),
    Column("currency", CURRENCY(), nullable=False),
    Column("issued_date", DATE(), nullable=True),
    Column("end_date", DATE(), nullable=True),
    Column("n_months", INT(), nullable=True),
    Column("status", TEXT(), nullable=True),
    Column("purpose", TEXT(), nullable=True),
    Column("created_at", TS(), nullable=False, server_default=sa.text("now()")),
    CheckConstraint("amount >= 0", name="ck_loans_amount_nonneg"),
)

# ---------- TRANSACTIONS ----------
t_transactions = Table(
    "transactions", metadata,
    UUID_PK,
    Column("legacy_id", sa.BigInteger(), nullable=True, unique=True),
    Column("user_id", UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("from_account_id", UUID(as_uuid=True), ForeignKey("public.accounts.id", ondelete="SET NULL"), nullable=True, index=True),
    Column("datetime", TS(), nullable=False),
    Column("amount", MONEY(), nullable=False),
    Column("currency", CURRENCY(), nullable=False),
    Column("category", TEXT(), nullable=True),
    Column("receiver", TEXT(), nullable=True),
    Column("description", TEXT(), nullable=True),
    Column("created_at", TS(), nullable=False, server_default=sa.text("now()")),
    CheckConstraint("amount >= 0", name="ck_tx_amount_nonneg"),
)

Index("ix_transactions_user_datetime", t_transactions.c.user_id, t_transactions.c.datetime)

# ---------- TELEGRAM USERS ----------
t_tg_users = Table(
    "tg_users", metadata,
    Column("telegram_id", sa.BigInteger(), primary_key=True),  # Telegram user id
    Column("username", TEXT(), nullable=True),
    Column("first_name", TEXT(), nullable=True),
    Column("last_name", TEXT(), nullable=True),
    Column("language_code", TEXT(), nullable=True),
    Column("is_premium", sa.Boolean(), nullable=True),
    Column("created_at", TS(), nullable=False, server_default=sa.text("now()")),
    Column("extra", JSONB, nullable=True),
)

# ---------- TG ↔ BANK USER LINKS ----------
t_user_links = Table(
    "user_links", metadata,
    UUID_PK,
    Column("telegram_id", sa.BigInteger(), ForeignKey("public.tg_users.telegram_id", ondelete="CASCADE"), nullable=False, index=True),
    Column("user_id", UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("status", TEXT(), nullable=False, server_default=sa.text("'pending'")),  # pending|verified|rejected
    Column("method", TEXT(), nullable=True),                                        # phone|email|code|csr_match|…
    Column("verified_at", TS(), nullable=True),
    Column("created_at", TS(), nullable=False, server_default=sa.text("now()")),
    sa.UniqueConstraint("telegram_id", "user_id", name="uq_user_links_telegram_user"),
)
