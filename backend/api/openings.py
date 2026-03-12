"""Openings API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db, get_mongodb
from models import User
from auth.dependencies import get_optional_user
from typing import Optional

router = APIRouter()


@router.get("/instances")
async def get_opening_instances(
    opening_name: Optional[str] = Query(None, description="Opening name to filter by"),
    opening_eco: Optional[str] = Query(None, description="Opening ECO code to filter by"),
    user_color: Optional[str] = Query(None, description="Filter by user color (white/black)"),
    job_id: Optional[str] = Query(None, description="Job ID for public analyses"),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Get problematic positions from specific openings.

    Returns instances where the user made mistakes in the opening,
    with full position data for interactive review.

    Supports both authenticated users (via current_user) and public analyses (via job_id).
    """
    if not opening_name and not opening_eco:
        raise HTTPException(
            status_code=400,
            detail="Either opening_name or opening_eco must be provided"
        )

    # Get MongoDB
    mongodb = get_mongodb()

    # Build query - support both user_id and job_id
    query = {
        "analyzed": True
    }

    if job_id:
        # Public analysis - use job_id
        query["job_id"] = job_id
    elif current_user:
        # Authenticated user - use user_id
        query["user_id"] = str(current_user.id)
    else:
        raise HTTPException(
            status_code=400,
            detail="Either job_id or authentication is required"
        )

    if opening_name:
        query["opening_name"] = opening_name
    if opening_eco:
        query["opening_eco"] = opening_eco
    if user_color:
        query["user_color"] = user_color

    # Fetch games with this opening
    games = await mongodb.games.find(query).to_list(length=100)

    instances = []

    for game in games:
        moves = game.get('moves', [])

        # Focus on opening phase (first 15 moves)
        opening_moves = [m for m in moves if m.get('move_number', 0) <= 15]

        # Find mistakes in the opening
        for move in opening_moves:
            if move.get('is_mistake') or move.get('is_blunder') or move.get('centipawn_loss', 0) > 50:
                instance = {
                    'game_id': str(game['_id']),
                    'fen': move.get('fen_before', ''),
                    'move_number': move.get('move_number'),
                    'move_played': move.get('san'),
                    'move_uci': move.get('move'),
                    'best_move': move.get('best_move'),
                    'eval_loss': move.get('centipawn_loss', 0),
                    'accuracy': move.get('accuracy', 0),
                    'is_mistake': move.get('is_mistake', False),
                    'is_blunder': move.get('is_blunder', False),
                    'date': game.get('date'),
                    'opening_name': game.get('opening_name'),
                    'opening_eco': game.get('opening_eco'),
                    'result': game.get('result'),
                    'user_color': game.get('user_color'),
                    'time_control': game.get('time_control')
                }
                instances.append(instance)

    # Sort by eval loss (worst mistakes first)
    instances.sort(key=lambda x: x['eval_loss'], reverse=True)

    return {
        'opening_name': opening_name,
        'opening_eco': opening_eco,
        'user_color': user_color,
        'instances': instances,
        'total_instances': len(instances)
    }
