import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum, Uuid, JSON, Boolean, Float, Integer
from sqlalchemy.orm import relationship
import enum

from database import Base

class ApplicationStatus(str, enum.Enum):
    SAVED = "SAVED"
    APPLIED = "APPLIED"
    INTERVIEWING = "INTERVIEWING"
    OFFERED = "OFFERED"
    REJECTED = "REJECTED"

class AuditLogStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    BLOCKED = "BLOCKED"

class User(Base):
    __tablename__ = "users"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    profile = relationship("Profile", uselist=False, back_populates="user", cascade="all, delete-orphan")
    ai_suggestions = relationship("AISuggestion", back_populates="user", cascade="all, delete-orphan")
    resume_versions = relationship("ResumeVersion", back_populates="user", cascade="all, delete-orphan")
    feedbacks = relationship("UserFeedback", back_populates="user", cascade="all, delete-orphan")

class Resume(Base):
    __tablename__ = "resumes"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    parsed_text = Column(Text, nullable=True)
    parsed_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="resumes")
    applications = relationship("Application", back_populates="resume")
    profiles = relationship("Profile", back_populates="resume")
    resume_versions = relationship("ResumeVersion", back_populates="base_resume", cascade="all, delete-orphan")

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    resume_id = Column(Uuid, ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True)
    raw_text = Column(Text, nullable=True)
    profile_json = Column(JSON, nullable=False)
    confirmed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="profile")
    resume = relationship("Resume", back_populates="profiles")

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String, nullable=False, index=True)
    company = Column(String, nullable=False, index=True)
    location = Column(String, nullable=True)
    job_url = Column(String, nullable=True)
    description = Column(Text, nullable=False)
    extracted_requirements = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    ai_suggestions = relationship("AISuggestion", back_populates="job", cascade="all, delete-orphan")
    resume_versions = relationship("ResumeVersion", back_populates="job", cascade="all, delete-orphan")

class Application(Base):
    __tablename__ = "applications"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_id = Column(Uuid, ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True, index=True)
    job_id = Column(Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.SAVED, nullable=False, index=True)
    applied_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    workflow_status = Column(String, default="JOB_SAVED", nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if "workflow_status" not in kwargs:
            self.workflow_status = "JOB_SAVED"

    user = relationship("User", back_populates="applications")
    resume = relationship("Resume", back_populates="applications")
    job = relationship("Job", back_populates="applications")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String, nullable=False)
    status = Column(Enum(AuditLogStatus), nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="audit_logs")

class AISuggestion(Base):
    __tablename__ = "ai_suggestions"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    section = Column(String, nullable=False)
    original_text = Column(Text, nullable=False)
    suggested_text = Column(Text, nullable=False)
    suggestion_type = Column(String, nullable=False)
    target_requirement = Column(String, nullable=False)
    rationale = Column(Text, nullable=False)
    evidence = Column(Text, nullable=False)
    evidence_status = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    requires_user_approval = Column(Boolean, default=True, nullable=False)
    status = Column(String, default="PENDING", nullable=False)  # PENDING, APPROVED, REJECTED, EDITED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="ai_suggestions")
    job = relationship("Job", back_populates="ai_suggestions")

class ResumeVersion(Base):
    __tablename__ = "resume_versions"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    base_resume_id = Column(Uuid, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, default="DRAFT", nullable=False)  # DRAFT, ACTIVE, INACTIVE
    content_json = Column(JSON, nullable=False)
    content_markdown = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="resume_versions")
    job = relationship("Job", back_populates="resume_versions")
    base_resume = relationship("Resume", back_populates="resume_versions")

class UserFeedback(Base):
    __tablename__ = "user_feedbacks"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    category = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="feedbacks")


