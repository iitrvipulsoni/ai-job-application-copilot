from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
import os
import uuid
import shutil
from datetime import datetime, timezone

from database import get_db
from models import Resume, User, Profile
from schemas import ResumeResponse, ProfileResponse
from routers.auth import get_current_user
from config import settings
from services.parser import extract_text_from_file, parse_resume_text

router = APIRouter(prefix="/resumes", tags=["resumes"])

@router.post("/upload", response_model=ResumeResponse)
def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a resume, validate file extension, save it locally,
    extract raw text, and save the record to the database.
    """
    file_extension = os.path.splitext(file.filename)[1].lower()
    
    # 1. Reject unsupported file types with clear errors
    if file_extension not in [".txt", ".md", ".pdf", ".docx"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{file_extension}'. Only .txt, .md, .pdf, and .docx are supported."
        )

    # Ensure uploads directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    file_id = uuid.uuid4()
    saved_file_name = f"{file_id}{file_extension}"
    saved_file_path = os.path.join(settings.UPLOAD_DIR, saved_file_name)
    
    try:
        with open(saved_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save file to disk: {str(e)}"
        )
        
    # 2. Extract plain text
    try:
        parsed_text = extract_text_from_file(saved_file_path, file.filename)
        # Generate initial parsed json profile details
        parsed_json = parse_resume_text(parsed_text)
    except HTTPException as he:
        # Clean up file on failure
        if os.path.exists(saved_file_path):
            os.remove(saved_file_path)
        raise he
    except Exception as e:
        if os.path.exists(saved_file_path):
            os.remove(saved_file_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process and extract text from resume: {str(e)}"
        )
    
    new_resume = Resume(
        id=file_id,
        user_id=current_user.id,
        file_name=file.filename,
        file_path=saved_file_path,
        parsed_text=parsed_text,
        parsed_json=parsed_json
    )
    
    db.add(new_resume)
    db.commit()
    db.refresh(new_resume)
    
    return new_resume

@router.post("/{resume_id}/parse", response_model=ProfileResponse)
def parse_resume(
    resume_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Parse an already uploaded resume by id.
    Creates or updates the candidate profile, setting confirmed=False.
    """
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found or access denied."
        )
        
    raw_text = resume.parsed_text or ""
    if not raw_text and os.path.exists(resume.file_path):
        raw_text = extract_text_from_file(resume.file_path, resume.file_name)
        resume.parsed_text = raw_text
        db.commit()
        
    # Run the deterministic segment parser
    profile_json = parse_resume_text(raw_text)
    
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        profile = Profile(
            user_id=current_user.id,
            resume_id=resume.id,
            raw_text=raw_text,
            profile_json=profile_json,
            confirmed=False
        )
        db.add(profile)
    else:
        profile.resume_id = resume.id
        profile.raw_text = raw_text
        profile.profile_json = profile_json
        profile.confirmed = False  # Always reset confirmation status on new parse runs
        profile.updated_at = datetime.now(timezone.utc)
        
    db.commit()
    db.refresh(profile)
    return profile

@router.get("", response_model=list[ResumeResponse])
def list_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all uploaded resumes.
    """
    return db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.created_at.desc()).all()

@router.get("/{resume_id}", response_model=ResumeResponse)
def get_resume(
    resume_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific resume's details.
    """
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found or access denied."
        )
    return resume
