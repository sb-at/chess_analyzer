"""Application configuration."""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""

    # Application
    app_name: str = "ChessMirror"
    debug: bool = True

    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://chessmirror:chessmirror_dev@localhost:5432/chessmirror"
    )
    mongodb_url: str = os.getenv(
        "MONGODB_URL",
        "mongodb://localhost:27017/chessmirror"
    )
    mongodb_database: str = "chessmirror"

    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # JWT
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret-key-change-in-production")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # OAuth - Chess.com
    chess_com_client_id: str = os.getenv("CHESS_COM_CLIENT_ID", "")
    chess_com_client_secret: str = os.getenv("CHESS_COM_CLIENT_SECRET", "")
    chess_com_redirect_uri: str = os.getenv(
        "CHESS_COM_REDIRECT_URI",
        "http://localhost:3000/auth/chess-com/callback"
    )

    # OAuth - Lichess
    lichess_client_id: str = os.getenv("LICHESS_CLIENT_ID", "")
    lichess_redirect_uri: str = os.getenv(
        "LICHESS_REDIRECT_URI",
        "http://localhost:3000/auth/lichess/callback"
    )

    # Stockfish
    stockfish_path: str = os.getenv("STOCKFISH_PATH", "/usr/games/stockfish")
    stockfish_depth: int = 18
    stockfish_threads: int = 4

    # Analysis
    max_games_import: int = 500
    analysis_batch_size: int = 10

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
