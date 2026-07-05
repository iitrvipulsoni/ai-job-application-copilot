from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid
from typing import List

from database import get_db
from models import User, Profile, Job, Resume, AISuggestion, ResumeVersion, AuditLog, AuditLogStatus, Application
from routers.auth import get_current_user
from schemas import ResumeVersionCreate, ResumeVersionResponse
from services.composer import compose_tailored_resume

router = APIRouter(prefix="/resume-versions", tags=["resume-versions"])

@router.post("", response_model=ResumeVersionResponse, status_code=status.HTTP_201_CREATED)
def create_resume_version(
    payload: ResumeVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a new versioned tailored resume based on approved/edited suggestions.
    """
    # 1. Fetch and verify confirmed candidate profile
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile or not profile.confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Candidate profile is not confirmed. Please review and confirm your profile first."
        )

    # 2. Fetch and verify job posting
    job = db.query(Job).filter(Job.id == payload.job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job posting not found or access denied."
        )

    if not job.extracted_requirements:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description requirements have not been analyzed yet."
        )

    # 3. Fetch active base resume
    base_resume = db.query(Resume).filter(Resume.user_id == current_user.id).first()
    if not base_resume:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No master resume found for candidate. Please upload a resume first."
        )

    # 4. Fetch suggestions and filter for APPROVED or EDITED
    suggestions = db.query(AISuggestion).filter(
        AISuggestion.user_id == current_user.id,
        AISuggestion.job_id == job.id
    ).all()

    approved_edited = [s for s in suggestions if s.status in ["APPROVED", "EDITED"]]
    if not approved_edited:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot generate resume version without at least one APPROVED or EDITED suggestion."
        )

    # 5. Compose tailored resume
    composed = compose_tailored_resume(base_resume, profile, approved_edited, job)

    # 6. Save new ResumeVersion record
    version = ResumeVersion(
        id=uuid.uuid4(),
        base_resume_id=base_resume.id,
        job_id=job.id,
        user_id=current_user.id,
        status="DRAFT",
        content_json=composed["content_json"],
        content_markdown=composed["content_markdown"]
    )
    db.add(version)

    # 7. Update Application workflow status
    app = db.query(Application).filter(
        Application.user_id == current_user.id,
        Application.job_id == job.id
    ).first()
    if app:
        app.workflow_status = "RESUME_VERSION_CREATED"

    db.commit()
    db.refresh(version)

    # 8. Log in audit_logs
    audit_entry = AuditLog(
        user_id=current_user.id,
        action="resume_version_created",
        status=AuditLogStatus.SUCCESS,
        details={
            "version_id": str(version.id),
            "job_id": str(job.id),
            "applied_suggestions_count": len(approved_edited)
        }
    )
    db.add(audit_entry)
    db.commit()

    return version

@router.get("", response_model=List[ResumeVersionResponse])
def list_resume_versions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all versioned resumes for the logged-in candidate.
    """
    versions = db.query(ResumeVersion).filter(
        ResumeVersion.user_id == current_user.id
    ).order_by(ResumeVersion.created_at.desc()).all()
    return versions

@router.get("/{id}", response_model=ResumeVersionResponse)
def get_resume_version_by_id(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve full details of a specific versioned resume.
    """
    version = db.query(ResumeVersion).filter(
        ResumeVersion.id == id,
        ResumeVersion.user_id == current_user.id
    ).first()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume version not found."
        )
    return version

@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_resume_version(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a versioned resume draft.
    """
    version = db.query(ResumeVersion).filter(
        ResumeVersion.id == id,
        ResumeVersion.user_id == current_user.id
    ).first()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume version not found."
        )
    
    job_id = version.job_id
    db.delete(version)
    db.commit()

    # Log in audit_logs
    audit_entry = AuditLog(
        user_id=current_user.id,
        action="resume_version_deleted",
        status=AuditLogStatus.SUCCESS,
        details={
            "version_id": str(id),
            "job_id": str(job_id)
        }
    )
    db.add(audit_entry)
    db.commit()

    return {"detail": "Resume version deleted successfully."}

@router.post("/{id}/activate", response_model=ResumeVersionResponse)
def activate_resume_version(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Activate a specific resume version for a job.
    Enforces one ACTIVE version per job, setting others to INACTIVE.
    """
    version = db.query(ResumeVersion).filter(
        ResumeVersion.id == id,
        ResumeVersion.user_id == current_user.id
    ).first()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume version not found."
        )

    # Deactivate all other versions for the same job and user
    db.query(ResumeVersion).filter(
        ResumeVersion.user_id == current_user.id,
        ResumeVersion.job_id == version.job_id,
        ResumeVersion.id != version.id
    ).update({"status": "INACTIVE"})

    # Mark this version active
    version.status = "ACTIVE"

    # Update Application workflow status
    app = db.query(Application).filter(
        Application.user_id == current_user.id,
        Application.job_id == version.job_id
    ).first()
    if app:
        app.workflow_status = "RESUME_VERSION_ACTIVE"

    db.commit()
    db.refresh(version)

    # Log in audit_logs
    audit_entry = AuditLog(
        user_id=current_user.id,
        action="resume_version_activated",
        status=AuditLogStatus.SUCCESS,
        details={
            "version_id": str(version.id),
            "job_id": str(version.job_id)
        }
    )
    db.add(audit_entry)
    db.commit()

    return version
