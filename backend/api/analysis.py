"""Analysis API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models import User, Job
from auth.dependencies import get_current_user
from tasks import analyze_games_batch_task, analyze_user_patterns_task

router = APIRouter()


class AnalyzeGamesRequest(BaseModel):
    """Analyze games request model."""
    limit: int = 100


class AnalyzeGamesResponse(BaseModel):
    """Analyze games response model."""
    job_id: str
    status: str
    message: str


class DetectPatternsResponse(BaseModel):
    """Detect patterns response model."""
    job_id: str
    status: str
    message: str


@router.post("/analyze-games", response_model=AnalyzeGamesResponse)
async def analyze_games(
    request: AnalyzeGamesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start game analysis job for unanalyzed games.

    This endpoint triggers Stockfish analysis for all unanalyzed games
    belonging to the current user.
    """
    # Create job record
    job = Job(
        user_id=current_user.id,
        job_type="analysis",
        status="pending",
        metadata={
            "limit": request.limit,
            "analysis_type": "stockfish"
        }
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Start background task
    analyze_games_batch_task.delay(
        job_id=str(job.id),
        user_id=str(current_user.id),
        limit=request.limit
    )

    return AnalyzeGamesResponse(
        job_id=str(job.id),
        status="pending",
        message=f"Game analysis started (up to {request.limit} games)"
    )


@router.post("/detect-patterns", response_model=DetectPatternsResponse)
async def detect_patterns(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start pattern detection job for analyzed games.

    This endpoint triggers pattern detection across all analyzed games
    to identify tactical, opening, and time management patterns.
    """
    # Create job record
    job = Job(
        user_id=current_user.id,
        job_type="pattern_detection",
        status="pending",
        metadata={
            "analysis_type": "patterns"
        }
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Start background task
    analyze_user_patterns_task.delay(
        job_id=str(job.id),
        user_id=str(current_user.id)
    )

    return DetectPatternsResponse(
        job_id=str(job.id),
        status="pending",
        message="Pattern detection started"
    )


@router.get("/stats")
async def get_analysis_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get analysis statistics for current user."""
    from database import get_mongodb
    import asyncio

    mongodb = get_mongodb()
    games_collection = mongodb.games

    user_id = str(current_user.id)

    # Count games by status
    total_games = await games_collection.count_documents({"user_id": user_id})
    analyzed_games = await games_collection.count_documents({
        "user_id": user_id,
        "analyzed": True
    })

    # Get recent job status
    recent_jobs = db.query(Job).filter(
        Job.user_id == current_user.id
    ).order_by(Job.created_at.desc()).limit(5).all()

    jobs_list = []
    for job in recent_jobs:
        jobs_list.append({
            "id": str(job.id),
            "type": job.job_type,
            "status": job.status,
            "progress": job.progress,
            "created_at": job.created_at,
            "completed_at": job.completed_at
        })

    return {
        "total_games": total_games,
        "analyzed_games": analyzed_games,
        "pending_analysis": total_games - analyzed_games,
        "analysis_percentage": round((analyzed_games / total_games * 100) if total_games > 0 else 0, 1),
        "recent_jobs": jobs_list
    }
