import os
from collections.abc import AsyncGenerator
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from ..config import get_settings

settings = get_settings()
# Create SQLModel engine
agent_db_engine = create_async_engine(settings.PG_AGENT_DATABASE_URL, future=True)
main_db_engine = create_async_engine(settings.PG_MAIN_DATABASE_URL, future=True)


async def get_agent_db_session() -> AsyncGenerator:
    async_session = async_sessionmaker(
        agent_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session


async def get_main_db_session() -> AsyncGenerator:
    async_session = async_sessionmaker(
        main_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
