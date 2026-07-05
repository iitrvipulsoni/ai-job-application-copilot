import os
import sys
import uuid
import pytest
from unittest.mock import MagicMock
from pydantic import BaseModel
from typing import List

# Add the apps/api folder to python path for importing modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/api")))

from services.ai_provider import MockProvider
from services.ai_orchestrator import (
    execute_ai_task,
    AIValidationError,
    GuardrailViolation
)
from services.guardrails import ProfileAlignmentGuardrail
from models import AuditLog, AuditLogStatus

class SimpleTestSchema(BaseModel):
    output_text: str
    status: str
    tags: List[str]

# 1. Mock Provider Response
def test_mock_provider_response():
    provider = MockProvider()
    
    # Text-only generation
    response = provider.generate(prompt="Hello")
    assert "mock text" in response.lower()
    
    # JSON-structured generation
    response_json = provider.generate(prompt="Hello", response_schema=SimpleTestSchema)
    import json
    parsed = json.loads(response_json)
    assert "output_text" in parsed
    assert "status" in parsed
    assert len(parsed["tags"]) > 0

# 2. Invalid JSON response blocked
def test_invalid_json_response_blocked():
    provider = MockProvider()
    
    with pytest.raises(AIValidationError) as exc_info:
        execute_ai_task(
            user_id=uuid.uuid4(),
            task_type="test",
            prompt_id="extract_requirements",
            input_variables={
                "title": "Backend Dev",
                "company": "Co",
                "location": "Remote",
                "description": "invalid_json_trigger"
            },
            output_schema=SimpleTestSchema,
            provider=provider
        )
        
    assert "Invalid JSON response" in str(exc_info.value)

# 3. Audit log creation
def test_audit_log_creation():
    mock_db = MagicMock()
    user_id = uuid.uuid4()
    
    execute_ai_task(
        user_id=user_id,
        task_type="test",
        prompt_id="extract_requirements",
        input_variables={
            "title": "Backend Dev",
            "company": "Co",
            "location": "Remote",
            "description": "Just a normal prompt"
        },
        output_schema=SimpleTestSchema,
        db=mock_db
    )
    
    mock_db.add.assert_called()
    called_args = [call[0][0] for call in mock_db.add.call_args_list]
    audit_logs = [obj for obj in called_args if isinstance(obj, AuditLog)]
    assert len(audit_logs) == 1
    assert audit_logs[0].action == "ai_request"
    assert audit_logs[0].status == AuditLogStatus.SUCCESS
    assert audit_logs[0].details["task_type"] == "test"
    assert audit_logs[0].details["prompt_id"] == "extract_requirements"
    assert audit_logs[0].details["validation_status"] == "success"
    assert "latency_ms" in audit_logs[0].details

# 4. Guardrail violation blocked
def test_guardrail_violation_blocked():
    mock_db = MagicMock()
    user_id = uuid.uuid4()
    
    profile_json = {
        "skills": ["Python", "FastAPI"]
    }
    
    guardrail = ProfileAlignmentGuardrail(profile_json)
    
    class BadProvider(MockProvider):
        def generate(self, prompt, system_instruction=None, response_schema=None, model_name=None):
            return '{"output_text": "Experienced in Kubernetes and scaling applications", "status": "success", "tags": ["Kubernetes"]}'

    provider = BadProvider()
    
    with pytest.raises(GuardrailViolation) as exc_info:
        execute_ai_task(
            user_id=user_id,
            task_type="test",
            prompt_id="extract_requirements",
            input_variables={
                "title": "Backend Dev",
                "company": "Co",
                "location": "Remote",
                "description": "normal description"
            },
            output_schema=SimpleTestSchema,
            guardrails=[guardrail],
            db=mock_db,
            provider=provider
        )
        
    assert "Blocked: Suggestion introduced 'Kubernetes'" in str(exc_info.value)
    
    called_args = [call[0][0] for call in mock_db.add.call_args_list]
    audit_logs = [obj for obj in called_args if isinstance(obj, AuditLog)]
    assert len(audit_logs) >= 1
    ai_log = [log for log in audit_logs if log.action == "ai_request"][-1]
    assert ai_log.status == AuditLogStatus.BLOCKED
    assert ai_log.details["validation_status"] == "blocked"
    assert "introduced 'Kubernetes'" in ai_log.details["error_message"]
