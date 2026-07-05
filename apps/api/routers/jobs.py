from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from database import get_db
from models import Job, User, AuditLog, AuditLogStatus
from schemas import JobCreate, JobUpdate, JobResponse
from routers.auth import get_current_user
from services.job_parser import parse_job_description

router = APIRouter(prefix="/jobs", tags=["jobs"])

def log_job_action(db: Session, user_id: uuid.UUID, action: str, job_id: uuid.UUID, details: dict):
    """
    Utility function to log CRUD job operations in the audit_logs table.
    """
    log = AuditLog(
        user_id=user_id,
        action=action,
        status=AuditLogStatus.SUCCESS,
        details={
            "job_id": str(job_id),
            **details
        }
    )
    db.add(log)
    db.commit()

@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a new job posting entry in the database.
    Rejects empty job descriptions with HTTP 400.
    """
    if not payload.description or not payload.description.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description cannot be empty."
        )
        
    new_job = Job(
        title=payload.title,
        company=payload.company,
        location=payload.location,
        job_url=payload.job_url,
        description=payload.description,
        user_id=current_user.id
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    log_job_action(db, current_user.id, "job_created", new_job.id, {
        "title": payload.title,
        "company": payload.company
    })
    
    return new_job

@router.get("", response_model=list[JobResponse])
def list_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all created jobs.
    """
    return db.query(Job).filter(Job.user_id == current_user.id).order_by(Job.created_at.desc()).all()

@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a single job's details and extracted requirements.
    """
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or access denied."
        )
    return job

@router.put("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: uuid.UUID,
    payload: JobUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a job details card. Rejects empty descriptions.
    """
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or access denied."
        )
        
    if payload.title is not None:
        job.title = payload.title
    if payload.company is not None:
        job.company = payload.company
    if payload.location is not None:
        job.location = payload.location
    if payload.job_url is not None:
        job.job_url = payload.job_url
    if payload.description is not None:
        if not payload.description.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job description cannot be empty."
            )
        job.description = payload.description
        
    db.commit()
    db.refresh(job)
    
    log_job_action(db, current_user.id, "job_updated", job.id, {
        "title": job.title,
        "company": job.company
    })
    
    return job

@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes a job from the database.
    """
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or access denied."
        )
        
    title = job.title
    company = job.company
    
    db.delete(job)
    db.commit()
    
    log_job_action(db, current_user.id, "job_deleted", job_id, {
        "title": title,
        "company": company
    })
    
    return None

@router.post("/{job_id}/analyze", response_model=JobResponse)
def analyze_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Run deterministic parser on the job description text and save
    the structured requirements inside the Job model.
    """
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or access denied."
        )
        
    # Execute deterministic parsing service
    parsed_data = parse_job_description(
        title=job.title,
        company=job.company,
        location=job.location,
        description=job.description
    )
    
    job.extracted_requirements = parsed_data
    db.commit()
    db.refresh(job)
    
    log_job_action(db, current_user.id, "job_analyzed", job.id, {
        "title": job.title,
        "company": job.company
    })
    
    return job
