"""Openings API routes."""
from fastapi import APIRouter, HTTPException, Query
from database import get_mongodb
from typing import Optional

router = APIRouter()


@router.get("/instances")
async def get_opening_instances(
    opening_name: Optional[str] = Query(None, description="Opening name to filter by"),
    opening_eco: Optional[str] = Query(None, description="Opening ECO code to filter by"),
    user_color: Optional[str] = Query(None, description="Filter by user color (white/black)"),
    job_id: Optional[str] = Query(None, description="Job ID for the analysis"),
):
    """Get problematic positions from specific openings.

    Returns instances where the user made mistakes in the opening,
    with full position data for interactive review.
    """
    if not opening_name and not opening_eco:
        raise HTTPException(
            status_code=400,
            detail="Either opening_name or opening_eco must be provided"
        )

    if not job_id:
        raise HTTPException(
            status_code=400,
            detail="job_id is required"
        )

    mongodb = get_mongodb()

    query = {
        "analyzed": True,
        "job_id": job_id
    }

    if opening_name:
        query["opening_name"] = opening_name
    if opening_eco:
        query["opening_eco"] = opening_eco
    if user_color:
        query["user_color"] = user_color

    games = await mongodb.games.find(query).to_list(length=100)

    instances = []

    for game in games:
        moves = game.get('moves', [])
        opening_moves = [m for m in moves if m.get('move_number', 0) <= 15]

        for move in opening_moves:
            if move.get('is_mistake') or move.get('is_blunder') or move.get('centipawn_loss', 0) > 50:
                instances.append({
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
                })

    instances.sort(key=lambda x: x['eval_loss'], reverse=True)

    return {
        'opening_name': opening_name,
        'opening_eco': opening_eco,
        'user_color': user_color,
        'instances': instances,
        'total_instances': len(instances)
    }
