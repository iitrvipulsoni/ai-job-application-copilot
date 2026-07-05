import os
import sys
import uuid
import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock

# Add apps/api to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/api")))

from services.job_parser import parse_job_description
from models import User, Job
from routers.jobs import create_job, analyze_job
from schemas import JobCreate

# 1. Reject empty job description test
def test_reject_empty_job_description():
    """
    Verifies that passing an empty or whitespace description raises an HTTP 400.
    """
    with pytest.raises(HTTPException) as exc_info:
        parse_job_description("Software Engineer", "Acme Corp", "Remote", "   ")
    assert exc_info.value.status_code == 400
    assert "Job description cannot be empty" in exc_info.value.detail

# 2. Extract years of experience test
def test_extract_years_experience():
    """
    Verifies regex extraction of minimum years of experience from description text.
    """
    # Pattern 1: "5+ years"
    parsed_1 = parse_job_description("Developer", "Acme", None, "Requires 5+ years of experience in JavaScript.")
    assert parsed_1["years_experience"] == 5

    # Pattern 2: "3 to 7 years"
    parsed_2 = parse_job_description("Developer", "Acme", None, "Need 3 to 7 years experience with SQL.")
    assert parsed_2["years_experience"] == 3

# 3. Extract required skills test
def test_extract_required_skills():
    """
    Verifies dictionary-based keyword matching inside description.
    """
    parsed = parse_job_description(
        "Full Stack Developer", "TechCo", None,
        "Requirements:\n- Must have expertise in TypeScript and Next.js\n- Preferred experience with Docker."
    )
    # TypeScript & Next.js should be in required section, Docker in preferred
    assert "TypeScript" in parsed["required_skills"]
    assert "Next.js" in parsed["required_skills"]
    assert "Docker" in parsed["tools"]

# 4. Create Job Route Test
def test_create_job_route():
    """
    Verifies that calling POST /jobs successfully inserts a record and triggers audit logging.
    """
    mock_db = MagicMock()
    mock_user = User(id=uuid.uuid4(), email="user@example.com")
    
    payload = JobCreate(
        title="Data Engineer",
        company="DataCorp",
        location="San Francisco, CA",
        job_url="https://datacorp.com/jobs/1",
        description="We are looking for a Data Engineer with 4 years experience."
    )
    
    response = create_job(payload=payload, db=mock_db, current_user=mock_user)
    
    assert response.title == "Data Engineer"
    assert response.company == "DataCorp"
    assert response.location == "San Francisco, CA"
    assert response.job_url == "https://datacorp.com/jobs/1"
    
    # Assert DB interaction
    mock_db.add.assert_called()
    mock_db.commit.assert_called()

# 5. Analyze Job Route Test (including Red Flags)
def test_analyze_job_route():
    """
    Verifies POST /jobs/{id}/analyze updates database with requirements JSON and catches red flags.
    """
    mock_db = MagicMock()
    mock_user = User(id=uuid.uuid4(), email="user@example.com")
    
    mock_job = Job(
        id=uuid.uuid4(),
        title="Lead Engineer",
        company="SpeedyStartup",
        location="Remote",
        job_url=None,
        description="Looking for a TypeScript ninja who loves a fast-paced environment and wears many hats!"
    )
    
    # Setup mock query chain
    mock_db.query.return_value.filter.return_value.first.return_value = mock_job
    
    response = analyze_job(job_id=mock_job.id, db=mock_db, current_user=mock_user)
    
    assert response.extracted_requirements is not None
    assert response.extracted_requirements["title"] == "Lead Engineer"
    assert "TypeScript" in response.extracted_requirements["required_skills"]
    
    # Flags checks
    flags = response.extracted_requirements["red_flags"]
    assert any("Ninja" in f for f in flags)
    assert any("Fast-paced" in f for f in flags)
    assert any("wear many hats" in f.lower() for f in flags)
    
    mock_db.commit.assert_called()
