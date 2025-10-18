from sqlalchemy import BigInteger, Column, Double, MetaData, Table, Text

metadata = MetaData()


t_accounts = Table(
    'accounts', metadata,
    Column('id', BigInteger),
    Column('user_id', BigInteger),
    Column('type', Text),
    Column('balance', Double(53)),
    Column('currency', Text),
    Column('interest_rate', BigInteger),
    Column('opened_at', Text),
    Column('ends_at', Text),
    schema='public'
)


t_financial_goals = Table(
    'financial_goals', metadata,
    Column('id', BigInteger),
    Column('user_id', BigInteger),
    Column('account_id', BigInteger),
    Column('name', Text),
    Column('target_amount', Double(53)),
    Column('current_amount', Double(53)),
    Column('currency', Text),
    Column('deadline', Text),
    Column('created_at', Text),
    Column('priority', Text),
    schema='public'
)


t_loans = Table(
    'loans', metadata,
    Column('id', BigInteger),
    Column('user_id', BigInteger),
    Column('account_id', BigInteger),
    Column('loan_type', Text),
    Column('amount', Double(53)),
    Column('currency', Text),
    Column('issued_date', Text),
    Column('end_date', Text),
    Column('n_months', BigInteger),
    Column('status', Text),
    Column('purpose', Text),
    Column('created_at', Text),
    schema='public'
)


t_transactions = Table(
    'transactions', metadata,
    Column('id', BigInteger),
    Column('user_id', BigInteger),
    Column('from_account_id', BigInteger),
    Column('datetime', Text),
    Column('amount', Double(53)),
    Column('currency', Text),
    Column('category', Text),
    Column('receiver', Text),
    Column('description', Text),
    schema='public'
)


t_users = Table(
    'users', metadata,
    Column('id', BigInteger),
    Column('name', Text),
    Column('email', Text),
    Column('sex', Text),
    Column('birth_date', Text),
    Column('city', Text),
    schema='public'
)
