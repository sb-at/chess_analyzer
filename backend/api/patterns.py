"""Patterns API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import User, Pattern
from auth.dependencies import get_current_user

router = APIRouter()


@router.get("/")
async def get_user_patterns(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all patterns for the current user."""
    patterns = db.query(Pattern).filter(
        Pattern.user_id == current_user.id
    ).order_by(
        (Pattern.severity * Pattern.frequency).desc()
    ).all()

    patterns_list = []
    for pattern in patterns:
        patterns_list.append({
            "id": str(pattern.id),
            "pattern_type": pattern.pattern_type,
            "pattern_subtype": pattern.pattern_subtype,
            "description": pattern.description,  # Human-readable description
            "severity": pattern.severity,
            "frequency": pattern.frequency,
            "first_seen": pattern.first_seen,
            "last_seen": pattern.last_seen,
            "examples": pattern.examples,
            "metadata": pattern.pattern_metadata
        })

    top_3 = patterns_list[:3]

    return {
        "top_3_blindspots": top_3,
        "all_patterns": patterns_list,
        "total_patterns": len(patterns_list)
    }


@router.get("/progress/history")
async def get_pattern_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get pattern progress history for the current user."""
    # TODO: Implement pattern progress tracking
    # This will fetch data from pattern_progress table
    return {
        "message": "Pattern progress tracking coming soon",
        "data": []
    }


@router.get("/{pattern_id}/instances")
async def get_pattern_instances(
    pattern_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed instances (positions) for a specific pattern."""
    from uuid import UUID
    from database import get_mongodb
    from bson import ObjectId
    import traceback

    print(f"[DEBUG] Getting instances for pattern_id: {pattern_id}")

    try:
        pattern_uuid = UUID(pattern_id)
    except ValueError as e:
        print(f"[ERROR] Invalid pattern ID: {pattern_id}, error: {e}")
        raise HTTPException(status_code=400, detail="Invalid pattern ID format")

    pattern = db.query(Pattern).filter(
        Pattern.id == pattern_uuid,
        Pattern.user_id == current_user.id
    ).first()

    if not pattern:
        print(f"[ERROR] Pattern not found: {pattern_uuid} for user {current_user.id}")
        raise HTTPException(status_code=404, detail="Pattern not found")

    print(f"[DEBUG] Found pattern: {pattern.pattern_type}/{pattern.pattern_subtype}")
    print(f"[DEBUG] Pattern has {len(pattern.examples or [])} examples")

    # Get MongoDB to fetch game details
    try:
        mongodb = get_mongodb()
    except Exception as e:
        print(f"[ERROR] Failed to get MongoDB connection: {e}")
        raise HTTPException(status_code=500, detail="Database connection error")

    instances = []
    examples = pattern.examples or []

    for idx, example in enumerate(examples):
        game_id = example.get('game_id')
        if not game_id:
            print(f"[WARN] Example {idx} missing game_id")
            continue

        # Fetch game from MongoDB
        try:
            print(f"[DEBUG] Fetching game {game_id} from MongoDB")
            game = await mongodb.games.find_one({"_id": ObjectId(game_id)})
            if not game:
                print(f"[WARN] Game not found in MongoDB: {game_id}")
                continue

            instance = {
                'game_id': str(game['_id']),
                'fen': example.get('fen', ''),
                'move_number': example.get('move_number'),
                'move_played': example.get('move') or example.get('san'),
                'best_move': example.get('best_move'),
                'eval_loss': example.get('eval_loss', 0),
                'date': example.get('date') or game.get('date'),
                'opening_name': game.get('opening_name'),
                'opening_eco': game.get('opening_eco'),
                'result': game.get('result'),
                'user_color': game.get('user_color'),
                'time_control': game.get('time_control'),
                'motif': example.get('motif'),
                # For defensive patterns
                'user_move': example.get('user_move'),
                'opponent_move': example.get('opponent_move')
            }

            instances.append(instance)
            print(f"[DEBUG] Successfully added instance {idx}")
        except Exception as e:
            print(f"[ERROR] Error fetching game {game_id}: {e}")
            print(traceback.format_exc())
            continue

    print(f"[DEBUG] Returning {len(instances)} instances")

    return {
        'pattern_id': str(pattern.id),
        'pattern_type': pattern.pattern_type,
        'pattern_subtype': pattern.pattern_subtype,
        'description': pattern.description,
        'instances': instances,
        'total_instances': len(instances)
    }


@router.get("/{pattern_id}")
async def get_pattern(
    pattern_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific pattern by ID."""
    from uuid import UUID

    try:
        pattern_uuid = UUID(pattern_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid pattern ID")

    pattern = db.query(Pattern).filter(
        Pattern.id == pattern_uuid,
        Pattern.user_id == current_user.id
    ).first()

    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    return {
        "id": str(pattern.id),
        "pattern_type": pattern.pattern_type,
        "pattern_subtype": pattern.pattern_subtype,
        "description": pattern.description,  # Human-readable description
        "severity": pattern.severity,
        "frequency": pattern.frequency,
        "first_seen": pattern.first_seen,
        "last_seen": pattern.last_seen,
        "examples": pattern.examples,
        "metadata": pattern.pattern_metadata
    }
