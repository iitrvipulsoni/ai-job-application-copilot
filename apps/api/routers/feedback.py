from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid
import os
from typing import List

from database import get_db
from models import User, UserFeedback, AuditLog, AuditLogStatus
from routers.auth import get_current_user
from schemas import FeedbackCreate, FeedbackResponse
from config import settings

router = APIRouter(prefix="/feedback", tags=["feedback"])

@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit user feedback/rating for the Private Beta.
    """
    if payload.rating < 1 or payload.rating > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be between 1 and 5 stars."
        )

    # Save to database
    feedback = UserFeedback(
        id=uuid.uuid4(),
        user_id=current_user.id,
        rating=payload.rating,
        category=payload.category,
        message=payload.message
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    # Log in audit logs
    audit_entry = AuditLog(
        user_id=current_user.id,
        action="feedback_submitted",
        status=AuditLogStatus.SUCCESS,
        details={
            "feedback_id": str(feedback.id),
            "rating": feedback.rating,
            "category": feedback.category
        }
    )
    db.add(audit_entry)
    db.commit()

    return feedback

@router.get("", response_model=List[FeedbackResponse])
def get_all_feedbacks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve all submitted feedbacks (Dev/Admin-only).
    Protected by ENABLE_DEV_ADMIN_ENDPOINTS=true environment variable.
    """
    if not settings.ENABLE_DEV_ADMIN_ENDPOINTS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin feedback retrieval endpoint is disabled in production."
        )

    feedbacks = db.query(UserFeedback).order_by(UserFeedback.created_at.desc()).all()
    return feedbacks
