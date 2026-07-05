from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid
from datetime import datetime, timezone

from database import get_db
from models import Profile, User
from schemas import ProfileResponse, ProfileUpdate
from routers.auth import get_current_user

router = APIRouter(prefix="/profile", tags=["profile"])

@router.get("", response_model=ProfileResponse)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve the active candidate profile for the logged-in user.
    """
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No candidate profile exists yet. Please upload and parse a resume to get started."
        )
    return profile

@router.put("", response_model=ProfileResponse)
def update_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update profile details. User can modify name, email, achievements,
    experience description, and skills. Resets confirmation status to False.
    """
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        # Create a new profile if none exists
        profile = Profile(
            user_id=current_user.id,
            profile_json=payload.profile_json.model_dump(),
            confirmed=False
        )
        db.add(profile)
    else:
        profile.profile_json = payload.profile_json.model_dump()
        profile.confirmed = False  # Reset confirmation upon editing
        profile.updated_at = datetime.now(timezone.utc)
        
    db.commit()
    db.refresh(profile)
    return profile

@router.post("/confirm", response_model=ProfileResponse)
def confirm_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Confirms the candidate profile, setting `confirmed=True`.
    """
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No candidate profile found to confirm. Please upload and parse a resume first."
        )
        
    profile.confirmed = True
    profile.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(profile)
    return profile
