from __future__ import annotations

import os
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from building_blocks.exceptions import AppException


def _build_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        return database_url

    legacy_user = os.getenv("POSTGRES_USER", "").strip()
    legacy_password = os.getenv("POSTGRES_PASSWORD", "").strip()
    legacy_db = os.getenv("POSTGRES_DB", "").strip()
    legacy_host = os.getenv("POSTGRES_HOST", "").strip()
    legacy_port = os.getenv("POSTGRES_PORT", "").strip()

    if all((legacy_user, legacy_password, legacy_db, legacy_host, legacy_port)):
        return (
            "postgresql+asyncpg://"
            f"{legacy_user}:{legacy_password}@{legacy_host}:{legacy_port}/{legacy_db}"
        )

    raise AppException(
        code="DATABASE_URL_MISSING",
        message="Thiếu DATABASE_URL trong môi trường",
        status_code=500,
    )


def _debug_enabled() -> bool:
    return os.getenv("DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def get_engine():
    return create_async_engine(_build_database_url(), echo=_debug_enabled())


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def init_db() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session():
    session_maker = get_session_maker()
    async with session_maker() as session:
        yield session
