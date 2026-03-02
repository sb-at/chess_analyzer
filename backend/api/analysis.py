"""Analysis API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Any
from database import get_db
from models import User, Job
from auth.dependencies import get_current_user
from tasks import analyze_games_batch_task, analyze_user_patterns_task, import_games_task
from constants import PLATFORM_CHESS_COM, PLATFORM_LICHESS, VALID_PLATFORMS
from bson import ObjectId
import uuid
import httpx

router = APIRouter()


def serialize_mongo_doc(doc: Any) -> Any:
    """Recursively convert MongoDB ObjectId fields to strings."""
    if isinstance(doc, ObjectId):
        return str(doc)
    elif isinstance(doc, dict):
        return {key: serialize_mongo_doc(value) for key, value in doc.items()}
    elif isinstance(doc, list):
        return [serialize_mongo_doc(item) for item in doc]
    else:
        return doc


class StartAnalysisRequest(BaseModel):
    """Start analysis request for any username (no auth required)."""
    platform: str  # PLATFORM_LICHESS or PLATFORM_CHESS_COM
    username: str
    limit: int = 10
    time_control: Optional[str] = None  # Optional time control filter


class StartAnalysisResponse(BaseModel):
    """Start analysis response."""
    job_id: str
    status: str
    message: str


@router.post("/start", response_model=StartAnalysisResponse)
async def start_analysis(
    request: StartAnalysisRequest,
    db: Session = Depends(get_db)
):
    """Start analysis for any username without authentication.

    This endpoint:
    1. Creates a temporary job record
    2. Imports games from the platform
    3. Analyzes games with Stockfish
    4. Detects patterns
    5. Returns results accessible via job_id
    """
    # Validate platform
    if request.platform not in VALID_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Platform must be '{PLATFORM_LICHESS}' or '{PLATFORM_CHESS_COM}'"
        )

    if not request.username or not request.username.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is required"
        )

    # Create a job record (without user_id for public analysis)
    job_metadata = {
        "platform": request.platform,
        "username": request.username.strip(),
        "limit": request.limit,
        "public_analysis": True
    }
    if request.time_control:
        job_metadata["time_control"] = request.time_control

    job = Job(
        user_id=None,  # No user required
        job_type="full_analysis",
        status="pending",
        job_metadata=job_metadata
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Start background task to import and analyze
    import_games_task.delay(
        job_id=str(job.id),
        user_id=None,  # No user ID for public analysis
        platform=request.platform,
        username=request.username.strip(),
        access_token=None,  # Public API doesn't need token
        limit=request.limit,
        time_control_filter=request.time_control
    )

    return StartAnalysisResponse(
        job_id=str(job.id),
        status="pending",
        message=f"Analysis started for {request.username} on {request.platform}"
    )


class GetTimeControlsRequest(BaseModel):
    """Get time controls request."""
    platform: str
    username: str
    sample_size: int = 100


class TimeControlInfo(BaseModel):
    """Time control information."""
    time_control: str
    display_name: str
    count: int
    category: str


class GetTimeControlsResponse(BaseModel):
    """Get time controls response."""
    username: str
    platform: str
    time_controls: list[TimeControlInfo]
    total_sampled: int


@router.post("/time-controls", response_model=GetTimeControlsResponse)
async def get_time_controls(request: GetTimeControlsRequest):
    """Get time controls played by a user by scanning their recent games.

    This endpoint quickly scans a user's recent games to identify which time controls
    they've played, allowing the user to filter analysis by time control.
    """
    from chess_import import ChessComClient, LichessClient
    from utils.time_control import categorize_time_control, format_display_name
    import asyncio

    # Validate platform
    if request.platform not in VALID_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Platform must be '{PLATFORM_LICHESS}' or '{PLATFORM_CHESS_COM}'"
        )

    if not request.username or not request.username.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is required"
        )

    try:
        # Get time controls based on platform
        if request.platform == PLATFORM_CHESS_COM:
            client = ChessComClient(request.username.strip())
            time_controls_dict, total_sampled = await client.get_time_controls_quick(
                sample_size=request.sample_size
            )
        else:  # PLATFORM_LICHESS
            client = LichessClient(request.username.strip(), token=None)
            time_controls_dict, total_sampled = await client.get_time_controls_quick(
                sample_size=request.sample_size
            )

        # Filter out time controls with < 5 games
        min_games = 5
        filtered_time_controls = {
            tc: count for tc, count in time_controls_dict.items()
            if count >= min_games
        }

        # If no time controls meet the minimum, use all of them anyway
        if not filtered_time_controls:
            filtered_time_controls = time_controls_dict

        # Build response with categorized and formatted time controls
        time_controls_list = []
        for time_control, count in filtered_time_controls.items():
            category = categorize_time_control(time_control)
            display_name = format_display_name(time_control, category)

            time_controls_list.append(TimeControlInfo(
                time_control=time_control,
                display_name=display_name,
                count=count,
                category=category
            ))

        # Sort by count (most played first)
        time_controls_list.sort(key=lambda x: x.count, reverse=True)

        return GetTimeControlsResponse(
            username=request.username.strip(),
            platform=request.platform,
            time_controls=time_controls_list,
            total_sampled=total_sampled
        )

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{request.username}' not found on {request.platform}"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch games from {request.platform}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error discovering time controls: {str(e)}"
        )


@router.get("/results/{job_id}")
async def get_analysis_results(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Get analysis results for a job without authentication.

    Returns job status, progress, and results (patterns) when complete.
    """
    from database import get_mongodb

    # Get job record
    job = db.query(Job).filter(Job.id == uuid.UUID(job_id)).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Build response
    response = {
        "job_id": str(job.id),
        "status": job.status,
        "progress": job.progress,
        "metadata": job.job_metadata,
        "created_at": job.created_at,
        "completed_at": job.completed_at
    }

    # If job is complete, include pattern results
    if job.status == "completed":
        mongodb = get_mongodb()
        patterns_collection = mongodb.patterns

        # For public analysis, we use job_id as the identifier
        # (since there's no user_id)
        patterns = await patterns_collection.find({
            "job_id": str(job.id)
        }).to_list(length=None)

        # Convert all ObjectId fields to strings
        patterns = [serialize_mongo_doc(pattern) for pattern in patterns]

        response["patterns"] = patterns

        # Get games for statistics
        games_collection = mongodb.games
        games = await games_collection.find({
            "job_id": str(job.id)
        }).to_list(length=None)

        response["games_analyzed"] = len(games)

        # Debug: check if games have opening info
        if games:
            sample_game = games[0]
            print(f"Sample game keys: {sample_game.keys()}")
            print(f"Sample game opening_name: {sample_game.get('opening_name')}")
            print(f"Sample game opening_eco: {sample_game.get('opening_eco')}")
            print(f"Sample game user_color: {sample_game.get('user_color')}")

        # Calculate opening statistics
        try:
            from utils.opening_stats import calculate_opening_statistics
            opening_stats = calculate_opening_statistics(games)
            print(f"Calculated opening stats: {opening_stats}")
            response["opening_stats"] = opening_stats
        except Exception as e:
            print(f"Error calculating opening statistics: {e}")
            import traceback
            traceback.print_exc()
            # Set empty opening stats if calculation fails
            response["opening_stats"] = {
                "white_openings": [],
                "black_openings": [],
                "total_white_games": 0,
                "total_black_games": 0
            }

    return response


class AnalyzeGamesRequest(BaseModel):
    """Analyze games request model."""
    limit: int = 10
    time_control: Optional[str] = None  # Optional time control filter


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
    job_metadata = {
        "limit": request.limit,
        "analysis_type": "stockfish"
    }
    if request.time_control:
        job_metadata["time_control"] = request.time_control

    job = Job(
        user_id=current_user.id,
        job_type="analysis",
        status="pending",
        job_metadata=job_metadata
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Start background task
    analyze_games_batch_task.delay(
        job_id=str(job.id),
        user_id=str(current_user.id),
        limit=request.limit,
        time_control=request.time_control
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
        job_metadata={
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

    # Get available time controls from user's games
    time_controls_pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$time_control", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    time_controls_cursor = games_collection.aggregate(time_controls_pipeline)
    time_controls_list = await time_controls_cursor.to_list(length=None)

    # Format time controls
    time_controls = []
    for tc in time_controls_list:
        if tc['_id'] and tc['count'] >= 3:  # Only include if 3+ games
            from utils.time_control import categorize_time_control, format_display_name
            category = categorize_time_control(tc['_id'])
            display_name = format_display_name(tc['_id'], category)
            time_controls.append({
                "time_control": tc['_id'],
                "display_name": display_name,
                "count": tc['count'],
                "category": category
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
        "time_controls": time_controls,
        "recent_jobs": jobs_list
    }
