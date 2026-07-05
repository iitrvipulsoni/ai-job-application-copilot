# Agent Guidelines: AI Job Application Copilot

This document outlines core principles, constraints, and instructions for AI agents modifying this codebase.

## Core Mandate: Truthful Customization
> [!CAUTION]
> Under no circumstances should this system fabricate achievements, falsify qualifications, or invent facts.

1. **Verify Evidence**: All customized resumes or letters must map strictly to verified facts from the user's uploaded master resume/profile.
2. **Never Auto-Apply**: The assistant must only prepare resources; the user must review and manually submit the application.
3. **Guardrails Policy**: Every AI generation request must pass through the `services/guardrails.py` validation framework. If any claims cannot be backed by the original resume, they must be flagged, removed, or logged in `audit_logs`.
4. **Resume Suggestions Integrity**:
   - Suggestions must not invent experience, tools, employers, metrics, certifications, degrees, or job titles.
   - Do not convert missing requirements into claimed experience.
   - If evidence is weak, mark as `REQUIRES_USER_CONFIRMATION`.
   - If unsupported, block the suggestion or classify it as `GAP_NOT_CLAIMED`.
   - Every suggestion must include evidence from the verified profile's `profile_json`.
   - All suggestions must default to `PENDING` status and require explicit user approval (`requires_user_approval = True`).
5. **Resume Versions Integrity**:
   - Never modify the original master resume.
   - Resume versions must only apply APPROVED and EDITED suggestions.
   - All tailored bullet points must maintain traceability metadata back to original text, suggestion IDs, and evidence.
   - Enforce one ACTIVE version per job; activating a version sets other versions for the same job to INACTIVE.

---

## Architectural Constraints
- **Frontend Stack**: Next.js App Router + TypeScript. Use Vanilla CSS (CSS modules). Do not add TailwindCSS unless specifically asked.
- **Backend Stack**: FastAPI + SQLAlchemy + PostgreSQL. Keep database queries efficient and properly index foreign keys.
- **Database Migrations**: Update `models.py` and ensure they align with the database. Keep schema changes fully relational.
- **Environment Variables**: Add new configuration parameters to `.env.example`. Do not commit actual credentials.

---

## Coding Conventions
- Use `pydantic` schemas for API payloads and response models.
- Maintain consistent error-handling responses: return detailed HTTP exceptions with structured error bodies.
- Log AI requests, responses, and blocked outputs in the `audit_logs` table for debugging and compliance.

---

## AI Layer & Orchestration Rules
- **No Direct AI Routing**: Under no circumstances should database or route layers make direct client requests to AI providers. All generation tasks must run through the `execute_ai_task` orchestrator.
- **Orchestration Declarations**: Every AI task must declare:
  - `prompt_id` and `prompt_version` registered in the central `PromptRegistry`.
  - `output_schema` defined as a Pydantic model for structural validation.
  - A suite of `guardrails` validating input and output constraints.
- **Guardrails Execution**: All output must be analyzed by guardrails to prevent skill hallucination.
- **Dev-Only Flag**: Any endpoint testing or demonstrating prompt/AI functionality must be marked dev-only and protected by the `ENABLE_DEV_AI_ENDPOINTS=true` environment check (disabled by default).

