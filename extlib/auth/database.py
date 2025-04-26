# extlib/auth/database.py
import os
from sqlalchemy import String, MetaData, DateTime 
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime,timezone
# Define the database URL (using a separate file for auth)
DATABASE_URL = os.environ.get("AUTH_DATABASE_URL", "sqlite+aiosqlite:///./auth.db")

# Create the async engine
engine = create_async_engine(DATABASE_URL, echo=bool(os.environ.get("DB_ECHO", False)))

# Create a configured "Session" class
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass

# --- User Database Model ---
class User(Base):
    __tablename__ = "users"

    # Your internal primary key - consider UUID if preferred
    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True) # Example: UUID as string
    firebase_uid: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    picture: Mapped[str | None] = mapped_column(String, nullable=True)
    # Add other fields like:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(), 
        nullable=False
    )
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', firebase_uid='{self.firebase_uid}')>"


async def create_db_and_tables():
    """Creates database tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables checked/created.")

async def get_async_session():
    """Dependency to get an async database session."""
    async with async_session_maker() as session:
        yield session