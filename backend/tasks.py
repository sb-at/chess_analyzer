"""Celery tasks for background processing."""
import sys
import os

# Ensure the app directory is in the Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from celery import Celery
from config import get_settings
from datetime import datetime, timezone
from constants import PLATFORM_CHESS_COM, PLATFORM_LICHESS

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
        time_control_filter: Optional time control category to filter games by (e.g., "bullet", "blitz", "rapid")
    """
    from database import SessionLocal, get_mongodb_sync
    from models import Job
    from chess_import import ChessComClient, LichessClient
    import asyncio
    from uuid import UUID

    # time_control_filter is now a category name ("bullet", "blitz", "rapid", etc.)
    # Games store exact time controls ("5+0", "3+2"), so we filter by category in Python
    from utils.time_control import categorize_time_control

    # Update job status
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == UUID(job_id)).first()

    if not job:
        return {"error": "Job not found"}

    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    db.commit()

    try:
        mongodb = get_mongodb_sync()
        games_collection = mongodb.games

        # Step 1: Check for existing games in database
        # Query by platform and player name (games where user played as white or black)
        existing_query = {
            "platform": platform,
            "$or": [
                {"white_player": username},
                {"black_player": username}
            ]
        }

        # time_control_filter is a category — fetch extra games and filter by category in Python
        db_fetch_limit = limit * 5 if time_control_filter else limit
        existing_games_raw = list(games_collection.find(existing_query).sort("date", -1).limit(db_fetch_limit))

        if time_control_filter:
            existing_games = [
                g for g in existing_games_raw
                if categorize_time_control(g.get("time_control", "")) == time_control_filter
            ][:limit]
        else:
            existing_games = existing_games_raw
        existing_count = len(existing_games)
        existing_game_ids = {game.get("game_id") for game in existing_games}

        print(f"Found {existing_count} existing games in database for {username} on {platform}")

        # Step 2: Fetch recent games from platform to check for new ones
        # Always fetch to check for new games, but limit the fetch size
        fetch_limit = max(limit, 100)  # Fetch at least 100 to check for new games
        if time_control_filter:
            fetch_limit = limit * 3  # Need more to account for time control filtering

        if platform == PLATFORM_CHESS_COM:
            client = ChessComClient(username)
            fetched_games = asyncio.run(client.import_recent_games(limit=fetch_limit))
        else:  # PLATFORM_LICHESS
            client = LichessClient(username, access_token)
            fetched_games = asyncio.run(client.import_recent_games(limit=fetch_limit))

        # Step 3: Identify new games (not in database)
        new_games = []
        for game in fetched_games:
            if game.get("game_id") not in existing_game_ids:
                new_games.append(game)

        # Filter new games by category
        if time_control_filter:
            new_games = [
                g for g in new_games
                if categorize_time_control(g.get("time_control", "")) == time_control_filter
            ]

        new_count = len(new_games)
        print(f"Found {new_count} new games on platform")

        # Step 4: Decide which games to use
        games_to_import = []
        total_imported = 0
        total_updated = 0

        if new_count >= limit:
            # We have enough new games - use only new games
            games_to_import = new_games[:limit]
            print(f"Using {len(games_to_import)} new games for analysis")
        elif new_count > 0:
            # We have some new games but not enough - combine with existing
            games_to_import = new_games
            needed_from_existing = limit - new_count
            games_to_import.extend(existing_games[:needed_from_existing])
            print(f"Using {new_count} new games + {needed_from_existing} existing games")
        else:
            # No new games - use existing games if we have enough
            if existing_count >= limit:
                games_to_import = existing_games[:limit]
                print(f"No new games found. Using {len(games_to_import)} existing games")
            else:
                # Not enough games total
                games_to_import = existing_games
                print(f"Only {existing_count} games available (requested {limit})")

        # Step 5: Import new games to MongoDB
        for i, game_data in enumerate(new_games):
            # Add user_id and job_id to game data
            game_data["user_id"] = user_id  # Can be None for public analysis
            game_data["job_id"] = job_id  # Always store job_id for retrieval
            game_data["created_at"] = datetime.now(timezone.utc)

            # Upsert game based on unique index (platform + game_id)
            query = {
                "platform": game_data["platform"],
                "game_id": game_data["game_id"]
            }

            # Remove first_imported from game_data to avoid conflict with $setOnInsert
            game_data_copy = {k: v for k, v in game_data.items() if k != "first_imported"}

            result = games_collection.update_one(
                query,
                {
                    "$set": game_data_copy,
                    "$setOnInsert": {"first_imported": datetime.now(timezone.utc)}
                },
                upsert=True
            )

            if result.upserted_id:
                total_imported += 1
            elif result.modified_count > 0:
                total_updated += 1

            # Update progress (50% for import, 50% for analysis)
            progress = int((i + 1) / len(new_games) * 25) if new_games else 0
            job.progress = progress
            db.commit()

        # Update only the games in games_to_import with job_id (not all existing games)
        # Create a set of game IDs that are in games_to_import for efficient lookup
        games_to_import_ids = {g.get("_id") for g in games_to_import if g.get("_id")}

        for game in existing_games:
            # Only update if this game is in our games_to_import list
            if game.get("_id") and game["_id"] in games_to_import_ids:
                games_collection.update_one(
                    {"_id": game["_id"]},
                    {"$set": {"job_id": job_id}}
                )

        # Use games_to_import for the rest of the analysis
        games = games_to_import
        job.processed_items = len(games)
        job.total_items = len(games)
        job.progress = 25
        db.commit()

        # If this is a full_analysis job, trigger analysis automatically
        if job.job_type == "full_analysis":
            # Trigger analysis of imported games
            from analysis.stockfish_analyzer_fast import FastStockfishAnalyzer

            analyzed_count = 0
            skipped_count = 0
            for i, game in enumerate(games):
                # Get the game from MongoDB - it should have job_id now
                # For existing games, we just updated them with job_id
                # For new games, they were imported with job_id
                saved_game = games_collection.find_one({
                    "platform": game.get("platform"),
                    "game_id": game.get("game_id")
                })

                if saved_game:
                    if saved_game.get('analyzed'):
                        # Game already analyzed - skip Stockfish analysis
                        skipped_count += 1
                        print(f"Skipping already analyzed game: {saved_game.get('game_id')}")
                    else:
                        # Game needs analysis
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
                                        "analyzed_at": datetime.now(timezone.utc)
                                    }
                                }
                            )
                            analyzed_count += 1
                        except Exception as e:
                            print(f"Error analyzing game {saved_game.get('game_id')}: {e}")

                # Update progress (25-90% for analysis)
                progress = 25 + int((i + 1) / len(games) * 65)
                job.progress = progress
                db.commit()

            print(f"Analysis complete: {analyzed_count} newly analyzed, {skipped_count} already analyzed")

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
                        "created_at": datetime.now(timezone.utc)
                    }
                    patterns_collection.insert_one(pattern_doc)

                job.progress = 100

        # Mark job as completed
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
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
        job.completed_at = datetime.now(timezone.utc)
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
                    "analyzed_at": datetime.now(timezone.utc)
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
    job.started_at = datetime.now(timezone.utc)
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
            job.completed_at = datetime.now(timezone.utc)
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
        job.completed_at = datetime.now(timezone.utc)
        job.progress = 100
        db.commit()

        return {
            "status": "completed",
            "total_analyzed": len(games)
        }

    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.now(timezone.utc)
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
    job.started_at = datetime.now(timezone.utc)
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
            job.completed_at = datetime.now(timezone.utc)
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
        job.completed_at = datetime.now(timezone.utc)
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
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise

    finally:
        db.close()
