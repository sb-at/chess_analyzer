"""Celery tasks for background processing."""
import sys
import os

# Ensure the app directory is in the Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
def import_games_task(self, job_id: str, user_id: str, platform: str, username: str, access_token: str, limit: int, time_control_filter: str = None):
    """Background task to import games from chess platform.

    Args:
        time_control_filter: Optional time control to filter games by (e.g., "3+0", "10+0")
    """
    from database import SessionLocal, get_mongodb_sync
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
        # If filtering by time control, fetch more games to account for filtering
        fetch_limit = limit * 3 if time_control_filter else limit

        # Import games based on platform
        if platform == "chess.com":
            client = ChessComClient(username)
            games = asyncio.run(client.import_recent_games(limit=fetch_limit))
        else:  # lichess
            client = LichessClient(username, access_token)
            games = asyncio.run(client.import_recent_games(limit=fetch_limit))

        # Filter games by time control if specified
        if time_control_filter:
            filtered_games = []
            for game in games:
                if game.get("time_control") == time_control_filter:
                    filtered_games.append(game)
                    if len(filtered_games) >= limit:
                        break
            games = filtered_games

            # Log filtering results
            print(f"Filtering games by time control: {time_control_filter}")
            print(f"Filtered to {len(games)} games matching time control")

        # Save games to MongoDB (using sync client)
        mongodb = get_mongodb_sync()
        games_collection = mongodb.games

        total_imported = 0
        total_updated = 0

        for i, game_data in enumerate(games):
            # Add user_id and job_id to game data
            game_data["user_id"] = user_id  # Can be None for public analysis
            game_data["job_id"] = job_id  # Always store job_id for retrieval
            game_data["created_at"] = datetime.utcnow()

            # Upsert game based on unique index (platform + game_id)
            # The unique index is on (platform, game_id), so we match on that
            query = {
                "platform": game_data["platform"],
                "game_id": game_data["game_id"]
            }

            result = games_collection.update_one(
                query,
                {
                    "$set": game_data,
                    "$setOnInsert": {"first_imported": datetime.utcnow()}
                },
                upsert=True
            )

            if result.upserted_id:
                total_imported += 1
            elif result.modified_count > 0:
                total_updated += 1

            # Update progress (50% for import, 50% for analysis)
            progress = int((i + 1) / len(games) * 50)
            job.progress = progress
            job.processed_items = i + 1
            job.total_items = len(games)
            db.commit()

        # If this is a full_analysis job, trigger analysis automatically
        if job.job_type == "full_analysis":
            # Trigger analysis of imported games
            from analysis.stockfish_analyzer_fast import FastStockfishAnalyzer

            analyzed_count = 0
            for i, game in enumerate(games):
                # Get the game from MongoDB to get its _id
                saved_game = games_collection.find_one({
                    "platform": game["platform"],
                    "game_id": game["game_id"],
                    "job_id": job_id
                })

                if saved_game and not saved_game.get('analyzed'):
                    try:
                        with FastStockfishAnalyzer(depth=10) as analyzer:
                            analysis = analyzer.analyze_game_fast(saved_game['pgn'], skip_opening_moves=8)

                        games_collection.update_one(
                            {"_id": saved_game["_id"]},
                            {
                                "$set": {
                                    "moves": analysis['moves_analysis'],
                                    "stats": analysis['stats'],
                                    "analyzed": True,
                                    "analyzed_at": datetime.utcnow()
                                }
                            }
                        )
                        analyzed_count += 1
                    except Exception as e:
                        print(f"Error analyzing game: {e}")

                # Update progress (50-90% for analysis)
                progress = 50 + int((i + 1) / len(games) * 40)
                job.progress = progress
                db.commit()

            # Trigger pattern detection
            from pattern_detection import PatternAggregator

            analyzed_games = list(games_collection.find({
                "job_id": job_id,
                "analyzed": True
            }))

            if len(analyzed_games) >= 5:
                aggregator = PatternAggregator()
                result = asyncio.run(aggregator.analyze_user_games(analyzed_games))

                # Save patterns to MongoDB (not PostgreSQL for public analysis)
                patterns_collection = mongodb.patterns

                for pattern_data in result.get('all_patterns', []):
                    pattern_doc = {
                        "job_id": job_id,
                        "user_id": user_id,  # Can be None
                        "pattern_type": pattern_data.get('pattern_type'),
                        "pattern_subtype": pattern_data.get('pattern_subtype'),
                        "description": pattern_data.get('description'),  # Human-readable description
                        "severity": pattern_data.get('severity'),
                        "frequency": pattern_data.get('frequency'),
                        "first_seen": pattern_data.get('first_seen'),
                        "last_seen": pattern_data.get('last_seen'),
                        "examples": pattern_data.get('examples'),
                        "metadata": pattern_data.get('metadata', {}),
                        "created_at": datetime.utcnow()
                    }
                    patterns_collection.insert_one(pattern_doc)

                job.progress = 100

        # Mark job as completed
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        if job.job_type != "full_analysis":
            job.progress = 100
        job.job_metadata = {
            **job.job_metadata,
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
    """Background task to analyze a single game with Stockfish (FAST VERSION)."""
    from database import get_mongodb_sync
    from analysis.stockfish_analyzer_fast import FastStockfishAnalyzer
    from bson import ObjectId

    try:
        mongodb = get_mongodb_sync()
        games_collection = mongodb.games

        # Get game from MongoDB
        game = games_collection.find_one({"_id": ObjectId(game_id)})

        if not game:
            return {"error": "Game not found"}

        if game.get('analyzed'):
            return {"status": "already_analyzed", "game_id": game_id}

        # Analyze game with Stockfish (FAST - only analyzes before moves, skips opening)
        with FastStockfishAnalyzer(depth=10) as analyzer:  # Depth 10 for speed
            analysis = analyzer.analyze_game_fast(game['pgn'], skip_opening_moves=8)

        # Update game with analysis
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

        return {
            "status": "completed",
            "game_id": game_id,
            "stats": analysis['stats']
        }

    except Exception as e:
        print(f"Error analyzing game {game_id}: {e}")
        return {"error": str(e), "game_id": game_id}


@celery_app.task(bind=True, name="tasks.analyze_games_batch_task")
def analyze_games_batch_task(self, job_id: str, user_id: str, limit: int = 100, time_control: str = None):
    """Background task to analyze multiple games in batch.

    Args:
        time_control: Optional time control filter (e.g., "3+0", "10+0")
    """
    from database import SessionLocal, get_mongodb_sync
    from models import Job
    from analysis import BatchGameAnalyzer
    from uuid import UUID

    db = SessionLocal()
    job = db.query(Job).filter(Job.id == UUID(job_id)).first()

    if not job:
        return {"error": "Job not found"}

    job.status = "running"
    job.started_at = datetime.utcnow()
    db.commit()

    try:
        mongodb = get_mongodb_sync()
        games_collection = mongodb.games

        # Build query for unanalyzed games
        query = {
            "user_id": user_id,
            "analyzed": {"$ne": True}
        }

        # Add time control filter if specified
        if time_control:
            query["time_control"] = time_control

        # Get unanalyzed games for user
        games = list(games_collection.find(query).limit(limit))

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
    from database import SessionLocal, get_mongodb_sync
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
        mongodb = get_mongodb_sync()
        games_collection = mongodb.games

        # Get analyzed games for user
        games = list(games_collection.find({
            "user_id": user_id,
            "analyzed": True
        }).sort("date", -1))

        if len(games) < 5:
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.job_metadata = {
                **job.job_metadata,
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
                description=pattern_data.get('description'),  # Human-readable description
                severity=pattern_data.get('severity'),
                frequency=pattern_data.get('frequency'),
                first_seen=pattern_data.get('first_seen'),
                last_seen=pattern_data.get('last_seen'),
                examples=pattern_data.get('examples'),
                pattern_metadata=pattern_data.get('metadata', {})
            )
            db.add(pattern)

        db.commit()

        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.progress = 100
        job.job_metadata = {
            **job.job_metadata,
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
