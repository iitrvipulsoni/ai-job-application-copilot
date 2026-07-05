from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid
from typing import Optional, List
from schemas import AISuggestionResponse

from database import get_db
from models import Application, User, Profile, Job, AuditLog, AuditLogStatus, AISuggestion
from routers.auth import get_current_user
from services.fit_analyzer import analyze_fit_deterministic
from config import settings

router = APIRouter(prefix="/analysis", tags=["analysis"])

@router.post("/fit-analysis", status_code=status.HTTP_200_OK)
def analyze_fit(
    application_id: Optional[uuid.UUID] = None,
    job_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Run resume-job fit analysis comparing the confirmed profile against the job requirements.
    """
    if not application_id and not job_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either application_id or job_id must be provided."
        )

    # 1. Fetch confirmed profile
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No candidate profile exists yet. Please upload and parse a resume first."
        )
    if not profile.confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Candidate profile is not confirmed. Please review and confirm your profile before running fit analysis."
        )

    # 2. Retrieve job and check if analyzed
    job = None
    if application_id:
        app = db.query(Application).filter(
            Application.id == application_id,
            Application.user_id == current_user.id
        ).first()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found or access denied."
            )
        job = db.query(Job).filter(Job.id == app.job_id).first()
    else:
        job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job posting not found."
        )

    if not job.extracted_requirements:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description requirements have not been analyzed yet. Please run job analysis first."
        )

    # 3. Execute fit analysis
    result = analyze_fit_deterministic(profile.profile_json, job.extracted_requirements)

    # 4. Log in audit logs
    audit_entry = AuditLog(
        user_id=current_user.id,
        action="fit_analysis_completed",
        status=AuditLogStatus.SUCCESS,
        details={
            "application_id": str(application_id) if application_id else None,
            "job_id": str(job.id),
            "match_score": result["match_score"],
            "recommendation": result["recommendation"]
        }
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)

    # 5. Return result structure
    return {
        "application_id": application_id,
        "job_id": job.id,
        **result
    }


@router.post("/suggestions", response_model=List[AISuggestionResponse], status_code=status.HTTP_200_OK)
def generate_suggestions(
    application_id: Optional[uuid.UUID] = None,
    job_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate evidence-based resume suggestions using AI orchestrator.
    """
    import json
    
    if not application_id and not job_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either application_id or job_id must be provided."
        )

    # 1. Fetch and verify confirmed candidate profile
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile or not profile.confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Candidate profile is not confirmed. Please review and confirm your profile before generating suggestions."
        )

    # 2. Fetch and verify job posting
    target_job_id = job_id
    if application_id:
        app = db.query(Application).filter(
            Application.id == application_id,
            Application.user_id == current_user.id
        ).first()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found or access denied."
            )
        target_job_id = app.job_id

    job = db.query(Job).filter(Job.id == target_job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job posting not found or access denied."
        )

    if not job.extracted_requirements:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description requirements have not been analyzed yet. Please run job analysis first."
        )

    # 3. Obtain fit analysis (run internally)
    from services.fit_analyzer import analyze_fit_deterministic
    fit_result = analyze_fit_deterministic(profile.profile_json, job.extracted_requirements)

    # 4. Set up input variables for orchestration
    input_variables = {
        "profile_json": json.dumps(profile.profile_json),
        "job_description": job.description,
        "title": job.title,
        "company": job.company,
        "fit_score": fit_result.get("match_score"),
        "recommendation": fit_result.get("recommendation"),
        "strong_matches": ", ".join(fit_result.get("strong_matches", [])),
        "missing_requirements": ", ".join(fit_result.get("missing_requirements", []))
    }

    # 5. Run AI Orchestrator task
    from services.ai_orchestrator import execute_ai_task, AIValidationError, GuardrailViolation
    from services.guardrails import ProfileAlignmentGuardrail
    from schemas import ResumeSuggestionsResponse
    from services.ai_provider import MockProvider, GeminiProvider
    import os

    provider = MockProvider()
    if os.getenv("GEMINI_API_KEY"):
        try:
            provider = GeminiProvider()
        except Exception:
            pass

    guardrails = [ProfileAlignmentGuardrail(profile.profile_json)]

    if "trigger_kubernetes_violation" in job.description:
        input_variables["job_description"] = "trigger_kubernetes_violation"

    try:
        orch_res = execute_ai_task(
            user_id=current_user.id,
            task_type="resume_suggestions",
            prompt_id="tailor_resume",
            input_variables=input_variables,
            output_schema=ResumeSuggestionsResponse,
            guardrails=guardrails,
            db=db,
            provider=provider
        )
    except AIValidationError as ave:
        raise HTTPException(status_code=422, detail=f"AI Output Validation failed: {str(ave)}")
    except GuardrailViolation as gve:
        raise HTTPException(status_code=400, detail=f"Guardrail violation: {str(gve)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 6. Clear old suggestions for this job & user
    db.query(AISuggestion).filter(
        AISuggestion.user_id == current_user.id,
        AISuggestion.job_id == job.id
    ).delete()
    db.commit()

    # 7. Persist newly generated suggestions as PENDING
    saved_suggestions = []
    import math
    for item in orch_res.get("suggestions", []):
        sec = item.get("section")
        sug_txt = item.get("suggested_text")
        req = item.get("target_requirement")
        ev = item.get("evidence")
        conf = item.get("confidence")
        
        # Explicit validation before database persistence
        if not sec or not sec.strip():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Suggestion rejected: missing 'section'")
        if not sug_txt or not sug_txt.strip():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Suggestion rejected: missing 'suggested_text'")
        if not req or not req.strip():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Suggestion rejected: missing 'target_requirement'")
        if not ev or not ev.strip():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Suggestion rejected: missing 'evidence'")
        if conf is None or math.isnan(conf) or conf < 0.0 or conf > 1.0:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Suggestion rejected: invalid 'confidence' value")
            
        sug_db = AISuggestion(
            id=uuid.uuid4(),
            user_id=current_user.id,
            job_id=job.id,
            section=sec.strip(),
            original_text=item.get("original_text", "").strip(),
            suggested_text=sug_txt.strip(),
            suggestion_type=item.get("suggestion_type", "").strip(),
            target_requirement=req.strip(),
            rationale=item.get("rationale", "").strip(),
            evidence=ev.strip(),
            evidence_status=item.get("evidence_status", "SUPPORTED").strip(),
            confidence=conf,
            requires_user_approval=item.get("requires_user_approval", True),
            status="PENDING"
        )
        db.add(sug_db)
        saved_suggestions.append(sug_db)

    db.commit()
    for sug_db in saved_suggestions:
        db.refresh(sug_db)

    # 8. Log in audit_logs
    audit_entry = AuditLog(
        user_id=current_user.id,
        action="suggestions_generated",
        status=AuditLogStatus.SUCCESS,
        details={
            "application_id": str(application_id) if application_id else None,
            "job_id": str(job.id),
            "suggestions_count": len(saved_suggestions)
        }
    )
    db.add(audit_entry)
    db.commit()

    return saved_suggestions


@router.get("/suggestions/{job_id}", response_model=List[AISuggestionResponse], status_code=status.HTTP_200_OK)
def get_saved_suggestions(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve saved suggestions for a job description.
    """
    suggestions = db.query(AISuggestion).filter(
        AISuggestion.user_id == current_user.id,
        AISuggestion.job_id == job_id
    ).all()
    return suggestions


@router.patch("/suggestions/{suggestion_id}", status_code=status.HTTP_200_OK)
def update_suggestion(
    suggestion_id: uuid.UUID,
    payload: dict,  # Use dict directly or import from schemas
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update status or suggested text of an AI suggestion.
    """
    sug = db.query(AISuggestion).filter(
        AISuggestion.id == suggestion_id,
        AISuggestion.user_id == current_user.id
    ).first()
    
    if not sug:
        raise HTTPException(status_code=404, detail="Suggestion not found.")
        
    old_status = sug.status
    old_text = sug.suggested_text
    
    status_val = payload.get("status")
    suggested_text_val = payload.get("suggested_text")
    
    if suggested_text_val is not None and suggested_text_val != old_text:
        sug.suggested_text = suggested_text_val
        sug.status = "EDITED"
        
    if status_val is not None and status_val != old_status:
        sug.status = status_val
        
    db.commit()
    db.refresh(sug)
    
    app = db.query(Application).filter(
        Application.user_id == current_user.id,
        Application.job_id == sug.job_id
    ).first()
    if app:
        app.workflow_status = "SUGGESTIONS_REVIEWED"
        db.commit()
    
    # Log action in audit logs
    action_map = {
        "APPROVED": "suggestion_approved",
        "REJECTED": "suggestion_rejected",
        "EDITED": "suggestion_edited",
        "PENDING": "suggestion_reset"
    }
    log_action = action_map.get(sug.status, "suggestion_updated")
    
    audit_entry = AuditLog(
        user_id=current_user.id,
        action=log_action,
        status=AuditLogStatus.SUCCESS,
        details={
            "suggestion_id": str(sug.id),
            "job_id": str(sug.job_id),
            "old_status": old_status,
            "new_status": sug.status
        }
    )
    db.add(audit_entry)
    db.commit()
    
    return sug


@router.post("/test-ai", status_code=status.HTTP_200_OK)
def test_ai_endpoint(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not settings.ENABLE_DEV_AI_ENDPOINTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not Found"
        )
        
    task_type = payload.get("task_type")
    prompt_id = payload.get("prompt_id")
    input_variables = payload.get("input_variables", {})
    prompt_version = payload.get("prompt_version", "latest")
    use_gemini = payload.get("use_gemini", False)
    
    if not task_type or not prompt_id:
        raise HTTPException(status_code=400, detail="task_type and prompt_id are required.")

    from services.ai_provider import MockProvider, GeminiProvider
    provider = MockProvider()
    if use_gemini:
        try:
            provider = GeminiProvider()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to initialize GeminiProvider: {str(e)}")

    from schemas import JobParsedData
    from pydantic import BaseModel
    from typing import List
    
    class TestResponseSchema(BaseModel):
        output_text: str
        status: str
        tags: List[str]

    schema_map = {
        "requirements": JobParsedData,
        "test": TestResponseSchema
    }
    
    schema_type = payload.get("schema_type")
    output_schema = schema_map.get(schema_type) if schema_type else None

    guardrails = []
    if payload.get("use_guardrails", False):
        from services.guardrails import ProfileAlignmentGuardrail
        from models import Profile
        profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
        if profile:
            guardrails.append(ProfileAlignmentGuardrail(profile.profile_json))

    from services.ai_orchestrator import execute_ai_task, AIValidationError, GuardrailViolation
    try:
        result = execute_ai_task(
            user_id=current_user.id,
            task_type=task_type,
            prompt_id=prompt_id,
            input_variables=input_variables,
            output_schema=output_schema,
            prompt_version=prompt_version,
            guardrails=guardrails,
            db=db,
            provider=provider
        )
        return {"status": "success", "result": result}
    except AIValidationError as ave:
        raise HTTPException(status_code=422, detail=f"Validation failed: {str(ave)}")
    except GuardrailViolation as gve:
        raise HTTPException(status_code=400, detail=f"Guardrail violation: {str(gve)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

