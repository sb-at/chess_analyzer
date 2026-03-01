"""Games API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db, get_mongodb
from models import User, Job
from auth.dependencies import get_current_user
from tasks import import_games_task
import uuid

router = APIRouter()


class ImportGamesRequest(BaseModel):
    """Import games request model."""
    platform: str  # "chess.com" or "lichess"
    limit: int = 500
    username: Optional[str] = None


class ImportGamesResponse(BaseModel):
    """Import games response model."""
    job_id: str
    status: str
    message: str


@router.post("/import", response_model=ImportGamesResponse)
async def import_games(
    request: ImportGamesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start game import job."""
    # Validate platform
    if request.platform not in ["chess.com", "lichess"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Platform must be 'chess.com' or 'lichess'"
        )

    # Get username
    if request.platform == "chess.com":
        username = request.username or current_user.chess_com_username
        access_token = current_user.chess_com_access_token
    else:
        username = request.username or current_user.lichess_username
        access_token = current_user.lichess_access_token

    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No {request.platform} username found for user"
        )

    # Create job record
    job = Job(
        user_id=current_user.id,
        job_type="import",
        status="pending",
        job_metadata={
            "platform": request.platform,
            "username": username,
            "limit": request.limit
        }
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Start background task
    import_games_task.delay(
        job_id=str(job.id),
        user_id=str(current_user.id),
        platform=request.platform,
        username=username,
        access_token=access_token,
        limit=request.limit
    )

    return ImportGamesResponse(
        job_id=str(job.id),
        status="pending",
        message=f"Game import started for {username} on {request.platform}"
    )


@router.get("/")
async def get_user_games(
    limit: int = 50,
    skip: int = 0,
    analyzed_only: bool = False,
    current_user: User = Depends(get_current_user)
):
    """Get user's games."""
    mongodb = get_mongodb()
    games_collection = mongodb.games

    # Build query
    query = {"user_id": str(current_user.id)}
    if analyzed_only:
        query["analyzed"] = True

    # Fetch games
    cursor = games_collection.find(query).sort("date", -1).skip(skip).limit(limit)
    games = await cursor.to_list(length=limit)

    # Convert ObjectId to string
    for game in games:
        game["_id"] = str(game["_id"])

    total = await games_collection.count_documents(query)

    return {
        "games": games,
        "total": total,
        "limit": limit,
        "skip": skip
    }


@router.get("/{game_id}")
async def get_game(
    game_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific game by ID."""
    mongodb = get_mongodb()
    games_collection = mongodb.games

    from bson import ObjectId

    try:
        game = await games_collection.find_one({
            "_id": ObjectId(game_id),
            "user_id": str(current_user.id)
        })
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found"
        )

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found"
        )

    game["_id"] = str(game["_id"])
    return game


@router.get("/stats/summary")
async def get_games_summary(
    current_user: User = Depends(get_current_user)
):
    """Get summary statistics of user's games."""
    mongodb = get_mongodb()
    games_collection = mongodb.games

    total_games = await games_collection.count_documents({"user_id": str(current_user.id)})
    analyzed_games = await games_collection.count_documents({
        "user_id": str(current_user.id),
        "analyzed": True
    })

    return {
        "total_games": total_games,
        "analyzed_games": analyzed_games,
        "pending_analysis": total_games - analyzed_games
    }
