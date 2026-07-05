import os
import sys
import uuid
import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock, patch

# Add apps/api to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/api")))

from routers.versions import create_resume_version, activate_resume_version, list_resume_versions
from services.composer import compose_tailored_resume
from models import User, Profile, Job, Resume, AISuggestion, ResumeVersion, Application, ApplicationStatus
from schemas import ResumeVersionCreate

# 1. Blocks unconfirmed profile
def test_blocks_unconfirmed_profile():
    mock_db = MagicMock()
    mock_user = User(id=uuid.uuid4(), email="candidate@example.com")
    
    unconfirmed_profile = Profile(
        user_id=mock_user.id,
        profile_json={"summary": "Orig Summary"},
        confirmed=False
    )
    
    mock_db.query.return_value.filter.return_value.first.return_value = unconfirmed_profile
    
    payload = ResumeVersionCreate(job_id=uuid.uuid4())
    
    with pytest.raises(HTTPException) as exc_info:
        create_resume_version(payload=payload, db=mock_db, current_user=mock_user)
        
    assert exc_info.value.status_code == 400
    assert "not confirmed" in exc_info.value.detail

# 2. Blocks if no approved/edited suggestions exist
def test_blocks_if_no_approved_or_edited_suggestions():
    mock_db = MagicMock()
    mock_user = User(id=uuid.uuid4(), email="candidate@example.com")
    
    confirmed_profile = Profile(
        user_id=mock_user.id,
        profile_json={"summary": "Orig Summary"},
        confirmed=True
      )
      
    mock_job = Job(
        id=uuid.uuid4(),
        title="Engineer",
        company="Tech",
        extracted_requirements={"required_skills": ["Python"]}
    )
    
    mock_resume = Resume(
        id=uuid.uuid4(),
        user_id=mock_user.id,
        file_name="resume.pdf",
        file_path="/path/to/resume.pdf"
    )
    
    # Return profile, job, resume sequentially
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        confirmed_profile,
        mock_job,
        mock_resume
    ]
    
    # Mock suggestions query to return only PENDING or REJECTED
    pending_suggestion = AISuggestion(
        id=uuid.uuid4(),
        status="PENDING",
        section="Summary",
        original_text="Orig Summary",
        suggested_text="New Summary"
    )
    rejected_suggestion = AISuggestion(
        id=uuid.uuid4(),
        status="REJECTED",
        section="Experience",
        original_text="Old bullet",
        suggested_text="Rejected bullet"
    )
    
    mock_db.query.return_value.filter.return_value.all.return_value = [
        pending_suggestion,
        rejected_suggestion
    ]
    
    payload = ResumeVersionCreate(job_id=mock_job.id)
    
    with pytest.raises(HTTPException) as exc_info:
        create_resume_version(payload=payload, db=mock_db, current_user=mock_user)
        
    assert exc_info.value.status_code == 400
    assert "without at least one APPROVED or EDITED suggestion" in exc_info.value.detail

# 3. Approved and Edited suggestions are applied, while master resume/profile remains unchanged
def test_composition_composer_rules():
    mock_user = User(id=uuid.uuid4(), email="candidate@example.com")
    
    profile_json = {
        "name": "Jane Doe",
        "summary": "Original summary line.",
        "work_experience": [
            {
                "company": "Stark Industries",
                "role": "Software Developer",
                "duration": "2022-2024",
                "achievements": [
                    "Wrote python scripts.",
                    "Unchanged bullet."
                ]
            }
        ],
        "skills": ["Python", "Git"],
        "tools": [],
        "projects": [],
        "certifications": []
    }
    
    confirmed_profile = Profile(
        user_id=mock_user.id,
        profile_json=profile_json,
        confirmed=True
    )
    
    mock_job = Job(
        id=uuid.uuid4(),
        title="Developer",
        company="Stark Industries",
        extracted_requirements={"required_skills": ["Python", "FastAPI"]}
    )
    
    mock_resume = Resume(
        id=uuid.uuid4(),
        user_id=mock_user.id,
        parsed_json=profile_json
    )
    
    approved_sug = AISuggestion(
        id=uuid.uuid4(),
        status="APPROVED",
        section="Summary",
        original_text="Original summary line.",
        suggested_text="Tailored summary line.",
        evidence="Python experience"
    )
    
    edited_sug = AISuggestion(
        id=uuid.uuid4(),
        status="EDITED",
        section="Experience - Stark Industries",
        original_text="Wrote python scripts.",
        suggested_text="Built robust Stark API web services in Python and FastAPI.",
        evidence="FastAPI project"
    )
    
    # Run compose service
    res = compose_tailored_resume(
        base_resume=mock_resume,
        profile=confirmed_profile,
        approved_suggestions=[approved_sug, edited_sug],
        job=mock_job
    )
    
    composed_json = res["content_json"]
    composed_md = res["content_markdown"]
    
    # Asserts
    # Summary suggestion applied
    assert composed_json["summary"] == "Tailored summary line."
    # Experience edited suggestion applied
    assert "Built robust Stark API web services in Python and FastAPI." in composed_json["work_experience"][0]["achievements"]
    # Unchanged bullet carried forward
    assert "Unchanged bullet." in composed_json["work_experience"][0]["achievements"]
    # Original bullet removed
    assert "Wrote python scripts." not in composed_json["work_experience"][0]["achievements"]
    
    # Traceability mappings
    assert str(approved_sug.id) in composed_json["_traceability"]
    assert str(edited_sug.id) in composed_json["_traceability"]
    assert composed_json["_traceability"][str(edited_sug.id)]["evidence"] == "FastAPI project"
    
    # Markdown matches composed text
    assert "Tailored summary line." in composed_md
    assert "Built robust Stark API web services in Python and FastAPI." in composed_md
    assert "Unchanged bullet." in composed_md

    # Master profile and resume remain completely untouched
    assert confirmed_profile.profile_json["summary"] == "Original summary line."
    assert confirmed_profile.profile_json["work_experience"][0]["achievements"][0] == "Wrote python scripts."

# 4. Activation enforces one ACTIVE version per job, setting others to INACTIVE
def test_activation_enforces_one_active_version():
    mock_db = MagicMock()
    mock_user = User(id=uuid.uuid4(), email="candidate@example.com")
    job_uuid = uuid.uuid4()
    
    active_version = ResumeVersion(
        id=uuid.uuid4(),
        user_id=mock_user.id,
        job_id=job_uuid,
        status="ACTIVE"
    )
    
    draft_version = ResumeVersion(
        id=uuid.uuid4(),
        user_id=mock_user.id,
        job_id=job_uuid,
        status="DRAFT"
    )
    
    # Mock db fetch
    mock_db.query.return_value.filter.return_value.first.return_value = draft_version
    
    # Mock Application update check
    mock_app = Application(
        user_id=mock_user.id,
        job_id=job_uuid,
        status=ApplicationStatus.SAVED,
        workflow_status="RESUME_VERSION_CREATED"
    )
    mock_db.query.return_value.filter.return_value.first.side_effect = [draft_version, mock_app]
    
    # Activate draft version
    result = activate_resume_version(id=draft_version.id, db=mock_db, current_user=mock_user)
    
    # Asserts
    assert result.status == "ACTIVE"
    assert mock_app.workflow_status == "RESUME_VERSION_ACTIVE"
    
    # Ensure update query deactivated other versions
    mock_db.query.return_value.filter.return_value.update.assert_called_once_with({"status": "INACTIVE"})

# 5. Listing version history works
def test_list_resume_versions():
    mock_db = MagicMock()
    mock_user = User(id=uuid.uuid4(), email="candidate@example.com")
    
    v1 = ResumeVersion(id=uuid.uuid4(), user_id=mock_user.id, status="ACTIVE")
    v2 = ResumeVersion(id=uuid.uuid4(), user_id=mock_user.id, status="DRAFT")
    
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [v1, v2]
    
    res = list_resume_versions(db=mock_db, current_user=mock_user)
    assert len(res) == 2
    assert res[0].status == "ACTIVE"
    assert res[1].status == "DRAFT"
