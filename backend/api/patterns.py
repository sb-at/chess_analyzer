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
