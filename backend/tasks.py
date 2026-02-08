"""Celery tasks for background processing."""
from celery import Celery
from config import get_settings
from datetime import datetime

settings = get_settings()

celery_app = Celery(
    'chess_analyzer',
    broker=settings.redis_url,
    backend=settings.redis_url
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)


@celery_app.task(bind=True, name="tasks.import_games_task")
def import_games_task(self, job_id: str, user_id: str, platform: str, username: str, access_token: str, limit: int):
    """Background task to import games from chess platform."""
    from database import SessionLocal, get_mongodb
    from models import Job
    from chess_import import ChessComClient, LichessClient
    import asyncio
    from uuid import UUID

    # Update job status
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == UUID(job_id)).first()

    if not job:
        return {"error": "Job not found"}

    job.status = "running"
    job.started_at = datetime.utcnow()
    db.commit()

    try:
        # Import games based on platform
        if platform == "chess.com":
            client = ChessComClient(username)
            games = asyncio.run(client.import_recent_games(limit=limit))
        else:  # lichess
            client = LichessClient(username, access_token)
            games = asyncio.run(client.import_recent_games(limit=limit))

        # Save games to MongoDB
        mongodb = get_mongodb()
        games_collection = mongodb.games

        total_imported = 0
        total_updated = 0

        for i, game_data in enumerate(games):
            # Add user_id to game data
            game_data["user_id"] = user_id
            game_data["created_at"] = datetime.utcnow()

            # Upsert game (update if exists, insert if not)
            result = asyncio.run(
                games_collection.update_one(
                    {
                        "platform": game_data["platform"],
                        "game_id": game_data["game_id"],
                        "user_id": user_id
                    },
                    {"$set": game_data},
                    upsert=True
                )
            )

            if result.upserted_id:
                total_imported += 1
            elif result.modified_count > 0:
                total_updated += 1

            # Update progress
            progress = int((i + 1) / len(games) * 100)
            job.progress = progress
            job.processed_items = i + 1
            job.total_items = len(games)
            db.commit()

        # Mark job as completed
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.progress = 100
        job.metadata = {
            **job.metadata,
            "total_imported": total_imported,
            "total_updated": total_updated,
            "total_games": len(games)
        }
        db.commit()

        return {
            "status": "completed",
            "total_imported": total_imported,
            "total_updated": total_updated,
            "total_games": len(games)
        }

    except Exception as e:
        # Mark job as failed
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        db.commit()

        raise

    finally:
        db.close()


@celery_app.task(bind=True, name="tasks.analyze_game_task")
def analyze_game_task(self, game_id: str, user_id: str):
    """Background task to analyze a single game with Stockfish."""
    # This will be implemented in Phase 2
    pass


@celery_app.task(bind=True, name="tasks.analyze_user_patterns_task")
def analyze_user_patterns_task(self, user_id: str):
    """Background task to detect patterns across all user games."""
    # This will be implemented in Phase 2
    pass
