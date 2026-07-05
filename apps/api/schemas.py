from pydantic import BaseModel, field_validator
from uuid import UUID
from datetime import datetime
from typing import List, Optional, Any
from models import ApplicationStatus, AuditLogStatus

# User
class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class UserResponse(BaseModel):
    id: UUID
    email: str
    created_at: datetime
    class Config:
        from_attributes = True

# Resume
class ResumeBase(BaseModel):
    file_name: str
    file_path: str

class ResumeResponse(ResumeBase):
    id: UUID
    user_id: UUID
    parsed_text: Optional[str] = None
    parsed_json: Optional[Any] = None
    created_at: datetime
    class Config:
        from_attributes = True

# Job
class JobParsedData(BaseModel):
    company: str
    title: str
    location: Optional[str] = None
    seniority: Optional[str] = None
    employment_type: Optional[str] = None
    responsibilities: List[str] = []
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    tools: List[str] = []
    domain_keywords: List[str] = []
    years_experience: Optional[int] = None
    education_requirements: Optional[str] = None
    certifications: List[str] = []
    soft_skills: List[str] = []
    red_flags: List[str] = []
    raw_job_text: str

class JobBase(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    job_url: Optional[str] = None
    description: str

class JobCreate(JobBase):
    pass

class JobUpdate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    job_url: Optional[str] = None
    description: Optional[str] = None

class JobResponse(JobBase):
    id: UUID
    extracted_requirements: Optional[JobParsedData] = None
    created_at: datetime
    class Config:
        from_attributes = True

# Application
class ApplicationBase(BaseModel):
    resume_id: Optional[UUID] = None
    status: ApplicationStatus = ApplicationStatus.SAVED
    notes: Optional[str] = None

class ApplicationCreate(ApplicationBase):
    title: str
    company: str
    description: Optional[str] = ""

class ApplicationUpdate(BaseModel):
    status: Optional[ApplicationStatus] = None
    resume_id: Optional[UUID] = None
    notes: Optional[str] = None

class ApplicationResponse(ApplicationBase):
    id: UUID
    user_id: UUID
    job_id: UUID
    applied_at: Optional[datetime] = None
    created_at: datetime
    job: JobResponse
    workflow_status: Optional[str] = None
    
    class Config:
        from_attributes = True

# AuditLog
class AuditLogResponse(BaseModel):
    id: UUID
    user_id: UUID
    action: str
    status: AuditLogStatus
    details: Optional[Any] = None
    created_at: datetime
    class Config:
        from_attributes = True

# Token
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[UUID] = None

# --- Sprint 2 Profile Schemas ---

class WorkExperienceItem(BaseModel):
    role: str
    company: str
    duration: str
    achievements: List[str] = []
    source_text: Optional[str] = None

class EducationItem(BaseModel):
    degree: str
    institution: str
    duration: str
    source_text: Optional[str] = None

class ProjectItem(BaseModel):
    name: str
    description: str
    source_text: Optional[str] = None

class ProfileData(BaseModel):
    name: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    location: Optional[str] = ""
    summary: Optional[str] = ""
    work_experience: List[WorkExperienceItem] = []
    education: List[EducationItem] = []
    skills: List[str] = []
    tools: List[str] = []
    projects: List[ProjectItem] = []
    certifications: List[str] = []
    achievements: List[str] = []
    metrics: List[str] = []
    low_confidence: Optional[bool] = False

class ProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    resume_id: Optional[UUID] = None
    raw_text: Optional[str] = None
    profile_json: ProfileData
    confirmed: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProfileUpdate(BaseModel):
    profile_json: ProfileData

class ResumeSuggestionItem(BaseModel):
    suggestion_id: str
    section: str
    original_text: str
    suggested_text: str
    suggestion_type: str
    target_requirement: str
    rationale: str
    evidence: str
    evidence_status: str  # SUPPORTED, REQUIRES_USER_CONFIRMATION, GAP_NOT_CLAIMED
    confidence: float
    requires_user_approval: bool = True

    @field_validator('section', 'suggested_text', 'target_requirement', 'evidence', 'suggestion_type')
    @classmethod
    def prevent_empty_strings(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace.")
        return v.strip()

    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        import math
        if math.isnan(v) or v < 0.0 or v > 1.0:
            raise ValueError("Confidence must be a valid float between 0.0 and 1.0.")
        return v

class ResumeSuggestionsResponse(BaseModel):
    job_id: str
    suggestions: List[ResumeSuggestionItem]

class AISuggestionUpdate(BaseModel):
    status: Optional[str] = None
    suggested_text: Optional[str] = None

class ResumeVersionCreate(BaseModel):
    job_id: UUID

class ResumeVersionResponse(BaseModel):
    id: UUID
    base_resume_id: UUID
    job_id: UUID
    user_id: UUID
    status: str
    content_json: ProfileData
    content_markdown: str
    created_at: datetime

    class Config:
        from_attributes = True

class UserRegister(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class FeedbackCreate(BaseModel):
    rating: int
    category: str
    message: str

class FeedbackResponse(BaseModel):
    id: UUID
    user_id: UUID
    rating: int
    category: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[UUID] = None
    email: Optional[str] = None

class AISuggestionResponse(BaseModel):
    id: UUID
    user_id: UUID
    job_id: UUID
    section: str
    original_text: str
    suggested_text: str
    suggestion_type: str
    target_requirement: str
    rationale: str
    evidence: str
    evidence_status: str
    confidence: float
    requires_user_approval: bool
    status: str

    class Config:
        from_attributes = True
