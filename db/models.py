import sqlalchemy as sa
from sqlalchemy import Column, ForeignKey, MetaData, Table, CheckConstraint, Index

metadata = MetaData(schema="public")

# Helpers
def INT_PK():
    return Column(
        "id",
        sa.Integer,
        primary_key=True,
        autoincrement=True
    )

MONEY    = lambda: sa.Numeric(14, 2)
PERCENT  = lambda: sa.Numeric(5, 2)
CURRENCY = lambda: sa.String(3)         # 'USD','KZT',...
TS       = lambda: sa.TIMESTAMP(timezone=True)
DATE     = lambda: sa.Date()
TEXT     = lambda: sa.Text()
INT      = lambda: sa.Integer()

# -------- users --------
t_users = Table(
    "users", metadata,
    INT_PK(),
    Column("name",       TEXT(), nullable=False),
    Column("email",      TEXT(), nullable=True, unique=True),
    Column("sex",        TEXT(), nullable=True),
    Column("birth_date", DATE(), nullable=True),
    Column("city",       TEXT(), nullable=True),
    Column("created_at", TS(),   nullable=False, server_default=sa.text("now()")),
)

# -------- accounts --------
t_accounts = Table(
    "accounts", metadata,
    INT_PK(),
    Column("user_id",     INT(), ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False),
    Column("type",        TEXT(),    nullable=False),
    Column("balance",     MONEY(),   nullable=False, server_default=sa.text("0")),
    Column("currency",    CURRENCY(),nullable=False),
    Column("interest_rate", PERCENT(), nullable=True),
    Column("opened_at",   DATE(),    nullable=True),
    Column("ends_at",     DATE(),    nullable=True),
    Column("created_at",  TS(),      nullable=False, server_default=sa.text("now()")),
    CheckConstraint("balance >= 0", name="ck_accounts_balance_nonneg"),
)
Index("ix_accounts_user_id", t_accounts.c.user_id)
Index("ix_accounts_user_currency", t_accounts.c.user_id, t_accounts.c.currency)

# -------- financial_goals --------
t_financial_goals = Table(
    "financial_goals", metadata,
    INT_PK(),
    Column("user_id",     INT(), ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False),
    Column("account_id",  INT(), ForeignKey("public.accounts.id", ondelete="CASCADE"), nullable=True),
    Column("name",          TEXT(),  nullable=False),
    Column("target_amount", MONEY(), nullable=False),
    Column("current_amount",MONEY(), nullable=False, server_default=sa.text("0")),
    Column("currency",      CURRENCY(), nullable=False),
    Column("deadline",      DATE(),   nullable=True),
    Column("created_at",    TS(),     nullable=False, server_default=sa.text("now()")),
    Column("priority",      TEXT(),   nullable=True),
    CheckConstraint("current_amount >= 0", name="ck_goals_current_nonneg"),
    CheckConstraint("target_amount >= 0", name="ck_goals_target_nonneg"),
)
Index("ix_goals_user_id", t_financial_goals.c.user_id)
Index("ix_goals_account_id", t_financial_goals.c.account_id)

# -------- loans --------
t_loans = Table(
    "loans", metadata,
    INT_PK(),
    Column("user_id",     INT(), ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False),
    Column("account_id",  INT(), ForeignKey("public.accounts.id", ondelete="SET NULL"), nullable=True),
    Column("loan_type",   TEXT(),    nullable=True),
    Column("amount",      MONEY(),   nullable=False),
    Column("currency",    CURRENCY(),nullable=False),
    Column("issued_date", DATE(),    nullable=True),
    Column("end_date",    DATE(),    nullable=True),
    Column("n_months",    INT(),     nullable=True),
    Column("status",      TEXT(),    nullable=True),
    Column("purpose",     TEXT(),    nullable=True),
    Column("created_at",  TS(),      nullable=False, server_default=sa.text("now()")),
    CheckConstraint("amount >= 0", name="ck_loans_amount_nonneg"),
)
Index("ix_loans_user_id", t_loans.c.user_id)
Index("ix_loans_account_id", t_loans.c.account_id)

# -------- transactions --------
t_transactions = Table(
    "transactions", metadata,
    INT_PK(),
    Column("user_id",         INT(), ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False),
    Column("from_account_id", INT(), ForeignKey("public.accounts.id", ondelete="SET NULL"), nullable=True),
    Column("datetime",        TS(),    nullable=False),
    Column("amount",          MONEY(), nullable=False),
    Column("currency",        CURRENCY(), nullable=False),
    Column("category",        TEXT(),  nullable=True),
    Column("receiver",        TEXT(),  nullable=True),
    Column("description",     TEXT(),  nullable=True),
    Column("created_at",      TS(),    nullable=False, server_default=sa.text("now()")),
    CheckConstraint("amount >= 0", name="ck_tx_amount_nonneg"),
)
Index("ix_transactions_user_id", t_transactions.c.user_id)
Index("ix_transactions_from_account_id", t_transactions.c.from_account_id)
Index("ix_transactions_user_datetime", t_transactions.c.user_id, t_transactions.c.datetime)
