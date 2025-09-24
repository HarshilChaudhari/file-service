# app/db.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import Base
from app.config import DATABASE_URL

# Async engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Async session maker
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Function to create tables
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
