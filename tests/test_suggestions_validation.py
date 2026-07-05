import os
import sys
import pytest
from pydantic import ValidationError

# Add the apps/api folder to python path for importing modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/api")))

from schemas import ResumeSuggestionItem, ResumeSuggestionsResponse

def test_resume_suggestion_validation_success():
    # Valid suggestion item
    item = {
        "suggestion_id": "sug-1",
        "section": "Summary",
        "original_text": "Old developer profile.",
        "suggested_text": "Results-driven Software Engineer with FastAPI experience.",
        "suggestion_type": "SKILL_HIGHLIGHT",
        "target_requirement": "FastAPI",
        "rationale": "Aligning summary skills to the FastAPI requirement.",
        "evidence": "Candidate lists FastAPI in their confirmed profile.",
        "evidence_status": "SUPPORTED",
        "confidence": 0.95,
        "requires_user_approval": True
    }
    
    validated = ResumeSuggestionItem.model_validate(item)
    assert validated.section == "Summary"
    assert validated.confidence == 0.95

def test_resume_suggestion_validation_empty_fields():
    # Empty suggested_text
    item_empty_text = {
        "suggestion_id": "sug-1",
        "section": "Summary",
        "original_text": "Old developer profile.",
        "suggested_text": "",  # Empty!
        "suggestion_type": "SKILL_HIGHLIGHT",
        "target_requirement": "FastAPI",
        "rationale": "Aligning summary skills to the FastAPI requirement.",
        "evidence": "Candidate lists FastAPI in their confirmed profile.",
        "evidence_status": "SUPPORTED",
        "confidence": 0.95
    }
    with pytest.raises(ValidationError) as exc:
        ResumeSuggestionItem.model_validate(item_empty_text)
    assert "Field cannot be empty or whitespace" in str(exc.value)

    # Empty target_requirement
    item_empty_req = {
        "suggestion_id": "sug-1",
        "section": "Summary",
        "original_text": "Old developer profile.",
        "suggested_text": "Results-driven Developer.",
        "suggestion_type": "SKILL_HIGHLIGHT",
        "target_requirement": "   ",  # Whitespace!
        "rationale": "Aligning summary skills to the FastAPI requirement.",
        "evidence": "Candidate lists FastAPI.",
        "evidence_status": "SUPPORTED",
        "confidence": 0.95
    }
    with pytest.raises(ValidationError) as exc:
        ResumeSuggestionItem.model_validate(item_empty_req)
    assert "Field cannot be empty or whitespace" in str(exc.value)

def test_resume_suggestion_validation_nan_confidence():
    # NaN confidence
    item_nan_conf = {
        "suggestion_id": "sug-1",
        "section": "Summary",
        "original_text": "Old developer profile.",
        "suggested_text": "Results-driven Developer.",
        "suggestion_type": "SKILL_HIGHLIGHT",
        "target_requirement": "FastAPI",
        "rationale": "Aligning summary skills.",
        "evidence": "Candidate lists FastAPI.",
        "evidence_status": "SUPPORTED",
        "confidence": float('nan')  # NaN!
    }
    with pytest.raises(ValidationError) as exc:
        ResumeSuggestionItem.model_validate(item_nan_conf)
    assert "Confidence must be a valid float between 0.0 and 1.0" in str(exc.value)
