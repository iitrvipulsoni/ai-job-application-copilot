import time
import json
from typing import Optional, Type, Dict, Any, List
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session
import uuid

from services.prompt_registry import registry
from services.ai_provider import AIProvider, MockProvider
from models import AuditLog, AuditLogStatus

class AIOrchestratorError(Exception):
    pass

class AIValidationError(AIOrchestratorError):
    pass

class GuardrailViolation(AIOrchestratorError):
    pass

def execute_ai_task(
    user_id: uuid.UUID,
    task_type: str,
    prompt_id: str,
    input_variables: Dict[str, Any],
    output_schema: Optional[Type[BaseModel]] = None,
    prompt_version: str = "latest",
    guardrails: Optional[List[Any]] = None,
    db: Optional[Session] = None,
    provider: Optional[AIProvider] = None,
    model_name: Optional[str] = None
) -> Any:
    """
    Orchestrates an AI task:
    1. Formats templates
    2. Runs input guardrails
    3. Invokes provider
    4. Validates JSON schema
    5. Runs output guardrails
    6. Logs telemetry to audit_logs
    """
    if provider is None:
        provider = MockProvider()
        
    prov_class_name = provider.__class__.__name__
    model = model_name or ("mock-model" if isinstance(provider, MockProvider) else "gemini-2.5-flash")

    # 1. Format templates
    try:
        system_instruction, user_template, actual_version = registry.get_prompt(prompt_id, prompt_version)
        formatted_user_prompt = user_template.format(**input_variables)
    except Exception as e:
        raise AIOrchestratorError(f"Prompt formatting failed: {str(e)}")

    start_time = time.perf_counter()
    latency_ms = 0
    validation_status = "success"
    error_message = None
    output_json = None

    # 2. Run input guardrails
    if guardrails:
        for gr in guardrails:
            if hasattr(gr, "validate_input"):
                try:
                    gr.validate_input(input_variables)
                except GuardrailViolation as gve:
                    latency_ms = int((time.perf_counter() - start_time) * 1000)
                    _log_telemetry(
                        db=db,
                        user_id=user_id,
                        task_type=task_type,
                        prompt_id=prompt_id,
                        prompt_version=actual_version,
                        provider=prov_class_name,
                        model=model,
                        input_json=input_variables,
                        output_json=None,
                        validation_status="blocked",
                        latency_ms=latency_ms,
                        error_message=str(gve),
                        status=AuditLogStatus.BLOCKED
                    )
                    raise gve

    # 3. Invoke provider
    raw_output = None
    try:
        raw_output = provider.generate(
            prompt=formatted_user_prompt,
            system_instruction=system_instruction,
            response_schema=output_schema,
            model_name=model
        )
    except Exception as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        error_message = f"AI Provider invocation failed: {str(e)}"
        _log_telemetry(
            db=db,
            user_id=user_id,
            task_type=task_type,
            prompt_id=prompt_id,
            prompt_version=actual_version,
            provider=prov_class_name,
            model=model,
            input_json=input_variables,
            output_json=None,
            validation_status="failed",
            latency_ms=latency_ms,
            error_message=error_message,
            status=AuditLogStatus.SUCCESS
        )
        raise AIOrchestratorError(error_message)

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    # 4. Parse & Validate JSON response
    parsed_output = None
    if output_schema:
        try:
            parsed_output = json.loads(raw_output)
            output_json = parsed_output
            
            validated_model = output_schema.model_validate(parsed_output)
            parsed_output = validated_model.model_dump()
        except json.JSONDecodeError as jde:
            validation_status = "failed"
            error_message = f"Invalid JSON response returned from AI provider: {str(jde)}"
            _log_telemetry(
                db=db,
                user_id=user_id,
                task_type=task_type,
                prompt_id=prompt_id,
                prompt_version=actual_version,
                provider=prov_class_name,
                model=model,
                input_json=input_variables,
                output_json=raw_output,
                validation_status="failed",
                latency_ms=latency_ms,
                error_message=error_message,
                status=AuditLogStatus.SUCCESS
            )
            raise AIValidationError(error_message)
        except ValidationError as ve:
            validation_status = "failed"
            error_message = f"JSON output does not match Pydantic schema: {str(ve)}"
            _log_telemetry(
                db=db,
                user_id=user_id,
                task_type=task_type,
                prompt_id=prompt_id,
                prompt_version=actual_version,
                provider=prov_class_name,
                model=model,
                input_json=input_variables,
                output_json=output_json,
                validation_status="failed",
                latency_ms=latency_ms,
                error_message=error_message,
                status=AuditLogStatus.SUCCESS
            )
            raise AIValidationError(error_message)
    else:
        output_json = raw_output

    # 5. Run output guardrails
    if guardrails:
        for gr in guardrails:
            if hasattr(gr, "validate_output"):
                try:
                    gr.validate_output(output_json or raw_output, input_variables)
                except GuardrailViolation as gve:
                    _log_telemetry(
                        db=db,
                        user_id=user_id,
                        task_type=task_type,
                        prompt_id=prompt_id,
                        prompt_version=actual_version,
                        provider=prov_class_name,
                        model=model,
                        input_json=input_variables,
                        output_json=output_json or raw_output,
                        validation_status="blocked",
                        latency_ms=latency_ms,
                        error_message=str(gve),
                        status=AuditLogStatus.BLOCKED
                    )
                    raise gve

    # 6. Log success telemetry
    _log_telemetry(
        db=db,
        user_id=user_id,
        task_type=task_type,
        prompt_id=prompt_id,
        prompt_version=actual_version,
        provider=prov_class_name,
        model=model,
        input_json=input_variables,
        output_json=output_json or raw_output,
        validation_status="success",
        latency_ms=latency_ms,
        error_message=None,
        status=AuditLogStatus.SUCCESS
    )

    return parsed_output if parsed_output is not None else raw_output

def _log_telemetry(
    db: Optional[Session],
    user_id: uuid.UUID,
    task_type: str,
    prompt_id: str,
    prompt_version: str,
    provider: str,
    model: str,
    input_json: Any,
    output_json: Any,
    validation_status: str,
    latency_ms: int,
    error_message: Optional[str],
    status: AuditLogStatus
):
    if db is None:
        return
        
    details = {
        "task_type": task_type,
        "prompt_id": prompt_id,
        "prompt_version": prompt_version,
        "provider": provider,
        "model": model,
        "input_json": input_json,
        "output_json": output_json,
        "validation_status": validation_status,
        "latency_ms": latency_ms,
        "error_message": error_message
    }
    
    log_entry = AuditLog(
        user_id=user_id,
        action="ai_request",
        status=status,
        details=details
    )
    
    try:
        db.add(log_entry)
        db.commit()
    except Exception:
        db.rollback()
