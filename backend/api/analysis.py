"""Analysis API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Any
from database import get_db
from models import Job
from tasks import import_games_task
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
    platform: str
    username: str
    limit: int = 10
    time_control: Optional[str] = None


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

    Imports games from the platform, analyzes with Stockfish, and detects patterns.
    Results are accessible via job_id.
    """
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

    job_metadata = {
        "platform": request.platform,
        "username": request.username.strip(),
        "limit": request.limit,
    }
    if request.time_control:
        job_metadata["time_control"] = request.time_control

    job = Job(
        user_id=None,
        job_type="full_analysis",
        status="pending",
        job_metadata=job_metadata
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    import_games_task.delay(
        job_id=str(job.id),
        user_id=None,
        platform=request.platform,
        username=request.username.strip(),
        access_token=None,
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
    """Get time controls played by a user by scanning their recent games."""
    from chess_import import ChessComClient, LichessClient
    from utils.time_control import categorize_time_control, format_display_name

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
        if request.platform == PLATFORM_CHESS_COM:
            client = ChessComClient(request.username.strip())
            time_controls_dict, total_sampled = await client.get_time_controls_quick(
                sample_size=request.sample_size
            )
        else:
            client = LichessClient(request.username.strip(), token=None)
            time_controls_dict, total_sampled = await client.get_time_controls_quick(
                sample_size=request.sample_size
            )

        min_games = 5
        filtered_time_controls = {
            tc: count for tc, count in time_controls_dict.items()
            if count >= min_games
        }

        if not filtered_time_controls:
            filtered_time_controls = time_controls_dict

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
    """Get analysis results for a job.

    Returns job status, progress, and results (patterns) when complete.
    """
    from database import get_mongodb

    job = db.query(Job).filter(Job.id == uuid.UUID(job_id)).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    response = {
        "job_id": str(job.id),
        "status": job.status,
        "progress": job.progress,
        "metadata": job.job_metadata,
        "created_at": job.created_at,
        "completed_at": job.completed_at
    }

    if job.status == "completed":
        mongodb = get_mongodb()
        patterns_collection = mongodb.patterns

        patterns = await patterns_collection.find({
            "job_id": str(job.id)
        }).to_list(length=None)

        patterns = [serialize_mongo_doc(pattern) for pattern in patterns]
        response["patterns"] = patterns

        games_collection = mongodb.games
        games = await games_collection.find({
            "job_id": str(job.id)
        }).to_list(length=None)

        response["games_analyzed"] = len(games)

        try:
            from utils.opening_stats import calculate_opening_statistics
            opening_stats = calculate_opening_statistics(games)
            response["opening_stats"] = opening_stats
        except Exception as e:
            print(f"Error calculating opening statistics: {e}")
            response["opening_stats"] = {
                "white_openings": [],
                "black_openings": [],
                "total_white_games": 0,
                "total_black_games": 0
            }

    return response


@router.get("/patterns/{pattern_id}/instances")
async def get_pattern_instances(
    pattern_id: str,
):
    """Get detailed instances for a pattern."""
    from database import get_mongodb
    import traceback

    mongodb = get_mongodb()

    try:
        pattern = await mongodb.patterns.find_one({"_id": ObjectId(pattern_id)})
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid pattern ID format: {str(e)}"
        )

    if not pattern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pattern not found"
        )

    instances = []
    for idx, example in enumerate(pattern.get('examples', [])):
        game_id = example.get('game_id')
        if not game_id:
            continue

        try:
            game = await mongodb.games.find_one({"_id": ObjectId(game_id)})
            if not game:
                continue

            instances.append({
                'game_id': str(game['_id']),
                'fen': example.get('fen', ''),
                'move_number': example.get('move_number'),
                'move_played': example.get('san') or example.get('move'),
                'best_move': example.get('best_move') or example.get('missed_move'),
                'eval_loss': example.get('eval_loss', 0),
                'date': example.get('date') or game.get('date'),
                'opening_name': game.get('opening_name'),
                'opening_eco': game.get('opening_eco'),
                'result': game.get('result'),
                'user_color': game.get('user_color'),
                'time_control': game.get('time_control'),
                'motif': example.get('motif'),
                'is_mistake': example.get('is_mistake', False),
                'is_blunder': example.get('is_blunder', False)
            })
        except Exception as e:
            print(f"[ERROR] Error fetching game {game_id}: {e}")
            traceback.print_exc()
            continue

    return {
        'pattern_id': str(pattern['_id']),
        'pattern_type': pattern.get('pattern_type'),
        'pattern_subtype': pattern.get('pattern_subtype'),
        'description': pattern.get('description'),
        'instances': instances,
        'total_instances': len(instances)
    }
