"""Database connection handlers."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from motor.motor_asyncio import AsyncIOMotorClient
from config import get_settings

settings = get_settings()

# PostgreSQL setup
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Get PostgreSQL database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# MongoDB setup
mongodb_client = AsyncIOMotorClient(settings.mongodb_url)
mongodb = mongodb_client[settings.mongodb_database]


def get_mongodb():
    """Get MongoDB database instance."""
    return mongodb


async def init_mongodb_indexes():
    """Initialize MongoDB indexes."""
    games = mongodb.games

    # Create indexes
    await games.create_index([("user_id", 1), ("date", -1)])
    await games.create_index([("user_id", 1), ("analyzed", 1)])
    await games.create_index([("platform", 1), ("game_id", 1)], unique=True)
    await games.create_index([("opening_eco", 1)])
    await games.create_index([("time_control", 1)])

    # Analysis cache indexes
    cache = mongodb.analysis_cache
    await cache.create_index([("fen", 1), ("depth", 1)], unique=True)
    await cache.create_index([("expires_at", 1)], expireAfterSeconds=0)
