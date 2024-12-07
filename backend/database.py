from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from fastapi import FastAPI

# Values "postgres:testpass" (username:password) and "localhost:5431" need to be personalized - **EDIT**
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5431/crypto_news"

# SQLAlchemy async engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Session factory
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Connecting to the database...")
    yield
    print("Disconnecting from the database...")
    await engine.dispose()

# Dependency to get the database session
async def get_db():
    async with SessionLocal() as session:
        yield session
