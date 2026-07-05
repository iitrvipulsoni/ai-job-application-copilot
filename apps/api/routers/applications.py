from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid
from datetime import datetime, timezone

from database import get_db
from models import Application, Job, User, ApplicationStatus
from schemas import ApplicationCreate, ApplicationUpdate, ApplicationResponse
from routers.auth import get_current_user

router = APIRouter(prefix="/applications", tags=["applications"])

@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new Job Application. Creates both the associated Job record
    and the Application link in a single transaction.
    """
    # 1. Create the associated Job
    new_job = Job(
        title=payload.title,
        company=payload.company,
        description=payload.description or "No description provided."
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    # 2. Create the Application
    applied_at = None
    if payload.status == ApplicationStatus.APPLIED:
        applied_at = datetime.now(timezone.utc)
        
    new_app = Application(
        user_id=current_user.id,
        resume_id=payload.resume_id,
        job_id=new_job.id,
        status=payload.status,
        notes=payload.notes,
        applied_at=applied_at
    )
    db.add(new_app)
    db.commit()
    db.refresh(new_app)
    
    return new_app

@router.get("", response_model=list[ApplicationResponse])
def list_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all active applications for the logged-in user.
    """
    return db.query(Application).filter(Application.user_id == current_user.id).order_by(Application.created_at.desc()).all()

@router.get("/{app_id}", response_model=ApplicationResponse)
def get_application(
    app_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a single application details.
    """
    app = db.query(Application).filter(Application.id == app_id, Application.user_id == current_user.id).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or access denied."
        )
    return app

@router.patch("/{app_id}", response_model=ApplicationResponse)
def update_application(
    app_id: uuid.UUID,
    payload: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update application status, notes, or change the linked resume.
    """
    app = db.query(Application).filter(Application.id == app_id, Application.user_id == current_user.id).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or access denied."
        )
        
    if payload.status is not None:
        # Update applied date if state is transitioning to APPLIED
        if payload.status == ApplicationStatus.APPLIED and app.status != ApplicationStatus.APPLIED:
            app.applied_at = datetime.now(timezone.utc)
        app.status = payload.status
        
    if payload.resume_id is not None:
        app.resume_id = payload.resume_id
        
    if payload.notes is not None:
        app.notes = payload.notes
        
    db.commit()
    db.refresh(app)
    return app

@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    app_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a job application from the tracker.
    """
    app = db.query(Application).filter(Application.id == app_id, Application.user_id == current_user.id).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or access denied."
        )
    db.delete(app)
    db.commit()
    return None
