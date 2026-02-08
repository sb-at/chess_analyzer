"""Jobs API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import User, Job
from auth.dependencies import get_current_user

router = APIRouter()


@router.get("/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get job status by ID."""
    from uuid import UUID

    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID")

    job = db.query(Job).filter(
        Job.id == job_uuid,
        Job.user_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "id": str(job.id),
        "job_type": job.job_type,
        "status": job.status,
        "progress": job.progress,
        "total_items": job.total_items,
        "processed_items": job.processed_items,
        "error_message": job.error_message,
        "metadata": job.metadata,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at
    }


@router.get("/")
async def get_user_jobs(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all jobs for the current user."""
    jobs = db.query(Job).filter(
        Job.user_id == current_user.id
    ).order_by(Job.created_at.desc()).limit(limit).all()

    jobs_list = []
    for job in jobs:
        jobs_list.append({
            "id": str(job.id),
            "job_type": job.job_type,
            "status": job.status,
            "progress": job.progress,
            "total_items": job.total_items,
            "processed_items": job.processed_items,
            "created_at": job.created_at,
            "completed_at": job.completed_at
        })

    return {
        "jobs": jobs_list,
        "total": len(jobs_list)
    }
