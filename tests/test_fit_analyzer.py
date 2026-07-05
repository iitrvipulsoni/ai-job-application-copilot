import os
import sys
import uuid
import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock, patch

# Add apps/api to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/api")))

from services.fit_analyzer import analyze_fit_deterministic, parse_total_experience_years
from routers.analysis import analyze_fit
from models import User, Profile, Job, AuditLog, AuditLogStatus

# 1. Blocks unconfirmed profile
def test_blocks_unconfirmed_profile():
    mock_db = MagicMock()
    mock_user = User(id=uuid.uuid4(), email="dev@example.com")
    
    # Unconfirmed profile
    unconfirmed_profile = Profile(
        user_id=mock_user.id,
        profile_json={"skills": ["Python"]},
        confirmed=False
    )
    
    mock_db.query.return_value.filter.return_value.first.return_value = unconfirmed_profile
    
    with pytest.raises(HTTPException) as exc_info:
        analyze_fit(job_id=uuid.uuid4(), db=mock_db, current_user=mock_user)
        
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
    
    mock_job = Job(id=uuid.uuid4(), title="Software Engineer", company="Co", description="...", extracted_requirements=None)
    
    mock_db.query.return_value.filter.return_value.first.side_effect = [confirmed_profile, mock_job]
    
    with pytest.raises(HTTPException) as exc_info:
        analyze_fit(job_id=mock_job.id, db=mock_db, current_user=mock_user)
        
    assert exc_info.value.status_code == 400
    assert "have not been analyzed yet" in exc_info.value.detail

# 3. Detects strong skill match
def test_detects_strong_skill_match():
    profile_json = {
        "skills": ["TypeScript", "Next.js"],
        "tools": ["Docker"],
        "work_experience": [
            {
                "role": "Software Engineer",
                "company": "SaaS Platform",
                "duration": "2023 - 2026",
                "achievements": [
                    "Developed frontend components using TypeScript and Next.js."
                ]
            }
        ]
    }
    
    extracted_requirements = {
        "required_skills": ["TypeScript"],
        "tools": ["Docker"]
    }
    
    result = analyze_fit_deterministic(profile_json, extracted_requirements)
    
    assert "TypeScript" in result["strong_matches"]
    assert "Docker" in result["strong_matches"]
    assert "TypeScript" in result["evidence_map"]
    assert "Developed frontend components" in result["evidence_map"]["TypeScript"]

# 4. Detects missing required skill
def test_detects_missing_required_skill():
    profile_json = {
        "skills": ["TypeScript"],
        "tools": ["Git"]
    }
    
    extracted_requirements = {
        "required_skills": ["Python"],
        "tools": ["Docker"]
    }
    
    result = analyze_fit_deterministic(profile_json, extracted_requirements)
    
    assert "Required Skill: Python" in result["missing_requirements"]
    assert "Required Tool: Docker" in result["missing_requirements"]

# 5. Calculates score deterministically
def test_calculates_score_deterministically():
    profile_json = {
        "skills": ["TypeScript", "Python"],
        "tools": ["Docker"],
        "work_experience": [
            {
                "role": "Dev",
                "company": "Co",
                "duration": "2023 - 2026",
                "achievements": ["TypeScript and Python developer"]
            }
        ]
    }
    
    extracted_requirements = {
        "required_skills": ["Python"],
        "preferred_skills": ["Kubernetes"],
        "tools": ["Docker"]
    }
    
    result = analyze_fit_deterministic(profile_json, extracted_requirements)
    
    assert result["match_score"] == 83
    assert result["recommendation"] == "APPLY"

# 6. Creates audit log
def test_creates_audit_log():
    mock_db = MagicMock()
    mock_user = User(id=uuid.uuid4(), email="dev@example.com")
    
    confirmed_profile = Profile(
        user_id=mock_user.id,
        profile_json={
            "skills": ["Python"],
            "tools": ["Docker"],
            "work_experience": []
        },
        confirmed=True
    )
    
    mock_job = Job(
        id=uuid.uuid4(),
        title="Python Dev",
        company="Co",
        description="...",
        extracted_requirements={
            "required_skills": ["Python"],
            "tools": ["Docker"]
        }
    )
    
    mock_db.query.return_value.filter.return_value.first.side_effect = [confirmed_profile, mock_job]
    
    response = analyze_fit(job_id=mock_job.id, db=mock_db, current_user=mock_user)
    
    assert response["match_score"] == 100
    
    mock_db.add.assert_called()
    called_args = [call[0][0] for call in mock_db.add.call_args_list]
    audit_logs = [obj for obj in called_args if isinstance(obj, AuditLog)]
    assert len(audit_logs) == 1
    assert audit_logs[0].action == "fit_analysis_completed"
    assert audit_logs[0].status == AuditLogStatus.SUCCESS
    assert audit_logs[0].details["match_score"] == 100
