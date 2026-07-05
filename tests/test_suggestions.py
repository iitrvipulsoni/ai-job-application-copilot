import os
import sys
import uuid
import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock, patch

# Add apps/api to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/api")))

from routers.analysis import generate_suggestions, get_saved_suggestions, update_suggestion
from models import User, Profile, Job, AuditLog, AuditLogStatus, AISuggestion

# 1. Blocks unconfirmed profile
def test_blocks_unconfirmed_profile():
    mock_db = MagicMock()
    mock_user = User(id=uuid.uuid4(), email="dev@example.com")
    
    unconfirmed_profile = Profile(
        user_id=mock_user.id,
        profile_json={"skills": ["Python"]},
        confirmed=False
    )
    
    mock_db.query.return_value.filter.return_value.first.return_value = unconfirmed_profile
    
    with pytest.raises(HTTPException) as exc_info:
        generate_suggestions(job_id=uuid.uuid4(), db=mock_db, current_user=mock_user)
        
    assert exc_info.value.status_code == 400
    assert "not confirmed" in exc_info.value.detail

# 2. Blocks unanalyzed job
def test_blocks_unanalyzed_job():
    mock_db = MagicMock()
    mock_user = User(id=uuid.uuid4(), email="dev@example.com")
    
    confirmed_profile = Profile(
        user_id=mock_user.id,
        profile_json={"skills": ["Python"]},
        confirmed=True
    )
    
    mock_job = Job(
        id=uuid.uuid4(),
        title="Software Engineer",
        company="Co",
        description="...",
        extracted_requirements=None
    )
    
    mock_db.query.return_value.filter.return_value.first.side_effect = [confirmed_profile, mock_job]
    
    with pytest.raises(HTTPException) as exc_info:
        generate_suggestions(job_id=mock_job.id, db=mock_db, current_user=mock_user)
        
    assert exc_info.value.status_code == 400
    assert "have not been analyzed yet" in exc_info.value.detail

# 3. Generated suggestions validate against schema and include evidence
def test_generated_suggestions_success():
    mock_db = MagicMock()
    mock_user = User(id=uuid.uuid4(), email="dev@example.com")
    
    confirmed_profile = Profile(
        user_id=mock_user.id,
        profile_json={
            "skills": ["Python", "FastAPI"],
            "work_experience": [
                {
                    "role": "Developer",
                    "company": "Company A",
                    "duration": "2 years",
                    "achievements": ["Developed FastAPI endpoints."]
                }
            ]
        },
        confirmed=True
    )
    
    mock_job = Job(
        id=uuid.uuid4(),
        title="FastAPI Engineer",
        company="Tech Corp",
        description="Must know Python and FastAPI.",
        extracted_requirements={
            "required_skills": ["Python", "FastAPI"],
            "preferred_skills": ["Docker"],
            "tools": [],
            "years_experience": 2,
            "education_requirements": [],
            "certifications": [],
            "soft_skills": [],
            "red_flags": [],
            "seniority": "Mid"
        }
    )
    
    mock_db.query.return_value.filter.return_value.first.side_effect = [confirmed_profile, mock_job]
    mock_db.query.return_value.filter.return_value.delete.return_value = 1
    
    suggestions = generate_suggestions(job_id=mock_job.id, db=mock_db, current_user=mock_user)
    
    assert len(suggestions) > 0
    for sug in suggestions:
        assert isinstance(sug, AISuggestion)
        assert sug.section
        assert sug.suggested_text
        assert sug.evidence
        assert sug.evidence_status in ["SUPPORTED", "REQUIRES_USER_CONFIRMATION", "GAP_NOT_CLAIMED"]
        assert sug.status == "PENDING"
        
    called_args = [call[0][0] for call in mock_db.add.call_args_list]
    audit_logs = [obj for obj in called_args if isinstance(obj, AuditLog)]
    assert len(audit_logs) >= 1
    assert any(log.action == "suggestions_generated" for log in audit_logs)

# 4. Unsupported skill claim is blocked
def test_unsupported_skill_claim_blocked():
    mock_db = MagicMock()
    mock_user = User(id=uuid.uuid4(), email="dev@example.com")
    
    confirmed_profile = Profile(
        user_id=mock_user.id,
        profile_json={
            "skills": ["Python", "FastAPI"],
            "work_experience": []
        },
        confirmed=True
    )
    
    mock_job = Job(
        id=uuid.uuid4(),
        title="Kubernetes Dev",
        company="Co",
        description="trigger_kubernetes_violation",
        extracted_requirements={
            "required_skills": ["Kubernetes"],
            "preferred_skills": [],
            "tools": [],
            "years_experience": 2,
            "education_requirements": [],
            "certifications": [],
            "soft_skills": [],
            "red_flags": [],
            "seniority": "Mid"
        }
    )
    
    mock_db.query.return_value.filter.return_value.first.side_effect = [confirmed_profile, mock_job]
    
    with pytest.raises(HTTPException) as exc_info:
        generate_suggestions(job_id=mock_job.id, db=mock_db, current_user=mock_user)
        
    assert exc_info.value.status_code == 400
    assert "Guardrail violation" in exc_info.value.detail

# 5. Approval status updates correctly
def test_approval_status_updates_correctly():
    mock_db = MagicMock()
    mock_user = User(id=uuid.uuid4(), email="dev@example.com")
    
    sug_id = uuid.uuid4()
    mock_suggestion = AISuggestion(
        id=sug_id,
        user_id=mock_user.id,
        job_id=uuid.uuid4(),
        section="Summary",
        original_text="Dev",
        suggested_text="FastAPI Dev",
        suggestion_type="SKILL_HIGHLIGHT",
        target_requirement="FastAPI",
        rationale="Match",
        evidence="FastAPI in skills",
        evidence_status="SUPPORTED",
        confidence=0.9,
        requires_user_approval=True,
        status="PENDING"
    )
    
    mock_db.query.return_value.filter.return_value.first.return_value = mock_suggestion
    
    updated = update_suggestion(suggestion_id=sug_id, payload={"status": "APPROVED"}, db=mock_db, current_user=mock_user)
    assert updated.status == "APPROVED"
    
    updated_rej = update_suggestion(suggestion_id=sug_id, payload={"status": "REJECTED"}, db=mock_db, current_user=mock_user)
    assert updated_rej.status == "REJECTED"
    
    updated_edit = update_suggestion(suggestion_id=sug_id, payload={"suggested_text": "Super FastAPI Dev"}, db=mock_db, current_user=mock_user)
    assert updated_edit.status == "EDITED"
    assert updated_edit.suggested_text == "Super FastAPI Dev"
    
    called_args = [call[0][0] for call in mock_db.add.call_args_list]
    audit_logs = [obj for obj in called_args if isinstance(obj, AuditLog)]
    assert len(audit_logs) >= 3
    actions = [log.action for log in audit_logs]
    assert "suggestion_approved" in actions
    assert "suggestion_rejected" in actions
    assert "suggestion_edited" in actions
