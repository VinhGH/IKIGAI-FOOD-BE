from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.building_blocks.infrastructure.config import envConfig
from sqlmodel import SQLModel
from typing import Optional

Base = SQLModel

engine = create_async_engine(
    envConfig.DATABASE_URL, 
    echo=envConfig.DEBUG,
    future=True
)


async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session():
    async with async_session_maker() as session:
        yield session