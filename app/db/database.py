# app/db/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.models import Base  # Import Base from your models file
from app.core.config import settings # Import settings

# Use DATABASE_URL from settings
DATABASE_URL = settings.DATABASE_URL

# Create the async engine
# Set echo=False for production to avoid logging every SQL query
engine = create_async_engine(DATABASE_URL, echo=True)

# Create a configured "AsyncSession" class
async_session_local = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

# Dependency to get a DB session in API routes
async def get_db() -> AsyncSession:
    async with async_session_local() as session:
        yield session

# Function to create database tables
async def init_db():
    async with engine.begin() as conn:
        # Use Base.metadata
        # await conn.run_sync(Base.metadata.drop_all) # Use drop_all carefully, only in dev
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables initialized.")

