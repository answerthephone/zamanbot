import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from sqlalchemy import Integer, String, Float, ForeignKey, DateTime, func

# ------------------------------------------
# 1️⃣ Base setup
# ------------------------------------------
DATABASE_URL = "postgresql+asyncpg://postgres:123@localhost:5432/mydd"

engine = create_async_engine(DATABASE_URL, echo=True)

class Base(DeclarativeBase):
    pass

# ------------------------------------------
# 2️⃣ Models
# ------------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="KZT")

    user = relationship("User", back_populates="accounts")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    from_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    category: Mapped[str] = mapped_column(String(50))
    date: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="transactions")


# ------------------------------------------
# 3️⃣ Seed function
# ------------------------------------------
async def seed_database():
    async with engine.begin() as conn:
        print("🔧 Creating all tables...")
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    print("🌱 Inserting seed data...")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Create users
        alice = User(name="Alice")
        bob = User(name="Bob")

        session.add_all([alice, bob])
        await session.flush()  # to get user IDs

        # Create accounts
        alice_acc = Account(user_id=alice.id, balance=50000, currency="KZT")
        bob_acc = Account(user_id=bob.id, balance=100000, currency="USD")

        session.add_all([alice_acc, bob_acc])
        await session.flush()

        # Create transactions
        txs = [
            Transaction(user_id=alice.id, from_account_id=alice_acc.id,
                        amount=15000, currency="KZT", category="Food"),
            Transaction(user_id=alice.id, from_account_id=alice_acc.id,
                        amount=20000, currency="KZT", category="Shopping"),
            Transaction(user_id=bob.id, from_account_id=bob_acc.id,
                        amount=500, currency="USD", category="Travel"),
        ]
        session.add_all(txs)

        await session.commit()
        print("✅ Seed data inserted successfully!")


# ------------------------------------------
# 4️⃣ Entry point
# ------------------------------------------
if __name__ == "__main__":
    asyncio.run(seed_database())
