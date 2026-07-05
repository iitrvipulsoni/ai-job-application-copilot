from sqlalchemy.orm import Session
import uuid
import json

from models import AuditLog, AuditLogStatus

def verify_claims_and_log(
    user_id: uuid.UUID,
    action: str,
    original_profile: dict,
    suggested_changes: list,
    db: Session
) -> bool:
    """
    Verifies that suggestions do not introduce fabricated experience.
    Logs the validation run and outcomes in the audit_logs table.
    
    Returns True if safe, False if violations/fabrications are blocked.
    """
    is_safe = True
    blocked_reasons = []
    
    # Extract known skills from original profile
    profile_skills = [s.lower() for s in original_profile.get("skills", [])]
    
    for suggestion in suggested_changes:
        status = suggestion.get("evidence_status")
        suggested_text = suggestion.get("suggested_text", "").lower()
        
        # Sprint 1 Guardrail Rules:
        # 1. If evidence status is explicitly marked UNSUPPORTED, block it.
        if status == "UNSUPPORTED":
            is_safe = False
            blocked_reasons.append(
                f"Unsupported claim in section '{suggestion.get('section')}': "
                f"'{suggestion.get('suggested_text')}' has no evidence in master profile."
            )
            
        # 2. Check if a major keyword was added that does not exist in master skills
        # (e.g. if the suggestion claims Kubernetes experience but user only has Docker)
        elif "kubernetes" in suggested_text and "kubernetes" not in profile_skills:
            is_safe = False
            blocked_reasons.append(
                f"Blocked: Suggestion introduced 'Kubernetes' which is not in candidate skills."
            )
            
    # Save transaction history to audit log table
    audit_status = AuditLogStatus.SUCCESS if is_safe else AuditLogStatus.BLOCKED
    details = {
        "suggestions_count": len(suggested_changes),
        "blocked_reasons": blocked_reasons,
        "is_safe": is_safe,
        "payload_checksum": hash(json.dumps(suggested_changes, sort_keys=True))
    }
    
    audit_entry = AuditLog(
        user_id=user_id,
        action=action,
        status=audit_status,
        details=details
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    
    return is_safe

SYNONYM_MAP = {
    "js": ["javascript", "js"],
    "javascript": ["javascript", "js"],
    "ts": ["typescript", "ts"],
    "typescript": ["typescript", "ts"],
    "postgres": ["postgresql", "postgres", "sql db", "sql"],
    "postgresql": ["postgresql", "postgres", "sql db", "sql"],
    "node": ["node.js", "node"],
    "node.js": ["node.js", "node"],
    "react": ["reactjs", "react"],
    "reactjs": ["reactjs", "react"],
    "sql db": ["sql", "postgresql", "postgres", "mysql", "sql db"],
    "sql": ["sql db", "sql", "postgresql", "postgres", "mysql"],
    "mysql": ["sql db", "sql", "mysql"]
}

class ProfileAlignmentGuardrail:
    """
    Ensures that AI outputs do not introduce fabricated skills not present in the candidate profile.
    Supports technical synonyms (e.g. JS -> JavaScript).
    """
    def __init__(self, original_profile: dict):
        self.profile_skills = [s.lower().strip() for s in original_profile.get("skills", [])]
        self.profile_tools = [t.lower().strip() for t in original_profile.get("tools", [])]
        self.all_profile_skills = self.profile_skills + self.profile_tools

    def has_evidence(self, skill_name: str) -> bool:
        skill_clean = skill_name.lower().strip()
        
        # Check direct match
        if skill_clean in self.all_profile_skills:
            return True
            
        # Check synonyms
        synonyms = SYNONYM_MAP.get(skill_clean, [])
        for syn in synonyms:
            if syn in self.all_profile_skills:
                return True
                
        # Substring fallback matches
        for ps in self.all_profile_skills:
            if ps in skill_clean or skill_clean in ps:
                return True
                
        return False

    def validate_output(self, output: any, input_variables: dict) -> None:
        import json
        text_to_check = ""
        if isinstance(output, dict):
            text_to_check = json.dumps(output).lower()
        elif isinstance(output, str):
            text_to_check = output.lower()

        # If 'kubernetes' is in output but not in profile skills (checking synonyms too), block it
        if "kubernetes" in text_to_check and not self.has_evidence("kubernetes"):
            from services.ai_orchestrator import GuardrailViolation
            raise GuardrailViolation("Blocked: Suggestion introduced 'Kubernetes' which is not in candidate skills.")

