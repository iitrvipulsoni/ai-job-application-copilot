import os
import sys
import uuid
import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock, patch

# Add apps/api to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/api")))

from services.guardrails import ProfileAlignmentGuardrail, SYNONYM_MAP
from services.ai_orchestrator import GuardrailViolation
from models import Application, User, Job, UserFeedback, ApplicationStatus
from routers.feedback import submit_feedback, get_all_feedbacks

# 1. Test ProfileAlignmentGuardrail Synonym Allowance
def test_guardrail_synonym_allowance():
    # User profile has "js" and "postgres"
    original_profile = {
        "skills": ["JS", "Postgres"],
        "tools": []
    }
    
    guardrail = ProfileAlignmentGuardrail(original_profile)
    
    # 1.1 "JS" and "JavaScript" should be allowed (synonym JS <=> JavaScript)
    assert guardrail.has_evidence("JavaScript") is True
    assert guardrail.has_evidence("js") is True
    
    # 1.2 "PostgreSQL" and "Postgres" should be allowed (synonym Postgres <=> PostgreSQL)
    assert guardrail.has_evidence("PostgreSQL") is True
    assert guardrail.has_evidence("postgres") is True
    
    # 1.3 "TypeScript" is not in profile skills, so has_evidence should return False
    assert guardrail.has_evidence("TypeScript") is False
    assert guardrail.has_evidence("kubernetes") is False

# 2. Test ProfileAlignmentGuardrail raises violation on missing skill (e.g. Kubernetes)
def test_guardrail_blocks_unsupported_skills():
    original_profile = {
        "skills": ["JavaScript", "React"],
        "tools": []
    }
    guardrail = ProfileAlignmentGuardrail(original_profile)
    
    # Should not raise violation for javascript
    guardrail.validate_output("This is a JavaScript role", {})
    
    # Should raise violation if Kubernetes is in output but not in profile
    with pytest.raises(GuardrailViolation) as exc_info:
        guardrail.validate_output("This is a Kubernetes role", {})
    assert "introduced 'Kubernetes'" in str(exc_info.value)

# 3. Test default Application workflow status
def test_application_default_workflow_status():
    app = Application(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        status=ApplicationStatus.SAVED
    )
    # The default workflow_status is 'JOB_SAVED'
    assert app.workflow_status == "JOB_SAVED"

# 4. Test feedback creation and list routes (mock db)
def test_feedback_routes():
    mock_db = MagicMock()
    mock_user = User(id=uuid.uuid4(), email="tester@example.com")
    
    from schemas import FeedbackCreate
    payload = FeedbackCreate(rating=5, category="General", message="Love the app!")
    
    # Mock database add
    feedback_obj = submit_feedback(payload=payload, db=mock_db, current_user=mock_user)
    
    assert feedback_obj.rating == 5
    assert feedback_obj.message == "Love the app!"
    assert feedback_obj.user_id == mock_user.id
    assert mock_db.add.called
    assert mock_db.commit.called

    # Mock list feedbacks (requires dev mode environment check)
    from config import settings
    with patch.object(settings, "ENABLE_DEV_ADMIN_ENDPOINTS", True):
        mock_db.query.return_value.order_by.return_value.all.return_value = [feedback_obj]
        feedbacks = get_all_feedbacks(db=mock_db, current_user=mock_user)
        assert len(feedbacks) == 1
        assert feedbacks[0].message == "Love the app!"
