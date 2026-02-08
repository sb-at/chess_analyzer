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
def analyze_game_task(self, game_id: str):
    """Background task to analyze a single game with Stockfish."""
    from database import get_mongodb
    from analysis import StockfishAnalyzer
    import asyncio
    from bson import ObjectId

    try:
        mongodb = get_mongodb()
        games_collection = mongodb.games

        # Get game from MongoDB
        game = asyncio.run(games_collection.find_one({"_id": ObjectId(game_id)}))

        if not game:
            return {"error": "Game not found"}

        if game.get('analyzed'):
            return {"status": "already_analyzed", "game_id": game_id}

        # Analyze game with Stockfish
        with StockfishAnalyzer() as analyzer:
            analysis = analyzer.analyze_game(game['pgn'])

        # Update game with analysis
        asyncio.run(
            games_collection.update_one(
                {"_id": ObjectId(game_id)},
                {
                    "$set": {
                        "moves": analysis['moves_analysis'],
                        "stats": analysis['stats'],
                        "analyzed": True,
                        "analyzed_at": datetime.utcnow()
                    }
                }
            )
        )

        return {
            "status": "completed",
            "game_id": game_id,
            "stats": analysis['stats']
        }

    except Exception as e:
        print(f"Error analyzing game {game_id}: {e}")
        return {"error": str(e), "game_id": game_id}


@celery_app.task(bind=True, name="tasks.analyze_games_batch_task")
def analyze_games_batch_task(self, job_id: str, user_id: str, limit: int = 100):
    """Background task to analyze multiple games in batch."""
    from database import SessionLocal, get_mongodb
    from models import Job
    from analysis import BatchGameAnalyzer
    import asyncio
    from uuid import UUID

    db = SessionLocal()
    job = db.query(Job).filter(Job.id == UUID(job_id)).first()

    if not job:
        return {"error": "Job not found"}

    job.status = "running"
    job.started_at = datetime.utcnow()
    db.commit()

    try:
        mongodb = get_mongodb()
        games_collection = mongodb.games

        # Get unanalyzed games for user
        cursor = games_collection.find({
            "user_id": user_id,
            "analyzed": {"$ne": True}
        }).limit(limit)

        games = asyncio.run(cursor.to_list(length=limit))

        if not games:
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.progress = 100
            db.commit()
            return {"status": "no_games_to_analyze"}

        job.total_items = len(games)
        db.commit()

        # Analyze games in batches
        analyzer = BatchGameAnalyzer()
        batch_size = 10

        for i in range(0, len(games), batch_size):
            batch = games[i:i + batch_size]
            analyzed = analyzer.analyze_games_batch(batch)

            # Update games in MongoDB
            for analyzed_game in analyzed:
                if analyzed_game.get('analyzed'):
                    asyncio.run(
                        games_collection.update_one(
                            {"_id": analyzed_game['_id']},
                            {
                                "$set": {
                                    "moves": analyzed_game['moves'],
                                    "stats": analyzed_game['stats'],
                                    "analyzed": True,
                                    "analyzed_at": analyzed_game['analyzed_at']
                                }
                            }
                        )
                    )

            # Update progress
            progress = int((i + len(batch)) / len(games) * 100)
            job.progress = progress
            job.processed_items = i + len(batch)
            db.commit()

        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.progress = 100
        db.commit()

        return {
            "status": "completed",
            "total_analyzed": len(games)
        }

    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        db.commit()
        raise

    finally:
        db.close()


@celery_app.task(bind=True, name="tasks.analyze_user_patterns_task")
def analyze_user_patterns_task(self, job_id: str, user_id: str):
    """Background task to detect patterns across all user games."""
    from database import SessionLocal, get_mongodb
    from models import Job, Pattern
    from pattern_detection import PatternAggregator
    import asyncio
    from uuid import UUID

    db = SessionLocal()
    job = db.query(Job).filter(Job.id == UUID(job_id)).first()

    if not job:
        return {"error": "Job not found"}

    job.status = "running"
    job.started_at = datetime.utcnow()
    db.commit()

    try:
        mongodb = get_mongodb()
        games_collection = mongodb.games

        # Get analyzed games for user
        cursor = games_collection.find({
            "user_id": user_id,
            "analyzed": True
        }).sort("date", -1)

        games = asyncio.run(cursor.to_list(length=None))

        if len(games) < 5:
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.metadata = {
                **job.metadata,
                "error": "Insufficient analyzed games (minimum 5 required)"
            }
            db.commit()
            return {"error": "Insufficient analyzed games"}

        # Run pattern detection
        aggregator = PatternAggregator()
        result = asyncio.run(aggregator.analyze_user_games(games))

        # Delete existing patterns for user
        db.query(Pattern).filter(Pattern.user_id == UUID(user_id)).delete()

        # Save new patterns to database
        for pattern_data in result.get('all_patterns', []):
            pattern = Pattern(
                user_id=UUID(user_id),
                pattern_type=pattern_data.get('pattern_type'),
                pattern_subtype=pattern_data.get('pattern_subtype'),
                severity=pattern_data.get('severity'),
                frequency=pattern_data.get('frequency'),
                first_seen=pattern_data.get('first_seen'),
                last_seen=pattern_data.get('last_seen'),
                examples=pattern_data.get('examples'),
                metadata=pattern_data.get('metadata', {})
            )
            db.add(pattern)

        db.commit()

        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.progress = 100
        job.metadata = {
            **job.metadata,
            "patterns_found": len(result.get('all_patterns', [])),
            "games_analyzed": result.get('analyzed_games_count')
        }
        db.commit()

        return {
            "status": "completed",
            "patterns_found": len(result.get('all_patterns', [])),
            "top_3_blindspots": result.get('top_3_blindspots', [])
        }

    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        db.commit()
        raise

    finally:
        db.close()
