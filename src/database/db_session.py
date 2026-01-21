# src/database/db_session.py
import os
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from typing import AsyncGenerator
from dotenv import load_dotenv
from sqlmodel import SQLModel
from utils.constant import DATABASE_URL

load_dotenv()

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for injecting database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database - create all tables."""
    
    # SQLModel uses SQLAlchemy metadata under the hood
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
