# AI Job Application Copilot

An AI-powered job application tailoring assistant that helps users modify their resumes and draft cover letters truthfully, based on evidence, without exaggerating experience or inventing achievements.

## Core Principle
**Truthful Customization Only.** The copilot must not:
- Auto-apply to jobs on behalf of the user.
- Fabricate work experience, achievements, or skills.
- Make resume claims that are unsupported by the user's uploaded master resume/profile.

---

## Directory Structure
```
job-application-copilot/
├── apps/
│   ├── web/        # Next.js (TypeScript, React) Frontend
│   └── api/        # FastAPI (Python) Backend
├── docs/           # Documentation and specs
├── tests/          # Testing suite
├── infra/          # Infrastructure configurations
├── docker-compose.yml
├── .env.example
├── README.md
└── AGENTS.md
```

---

## Technical Stack
- **Frontend**: Next.js (App Router), TypeScript, Vanilla CSS Modules
- **Backend**: FastAPI, SQLAlchemy, PostgreSQL, Python 3.10+
- **Database**: PostgreSQL (Dockerized or local instance)

---

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.10+
- Node.js 18+ & npm

### Setup Database
Start the database service:
```bash
docker-compose up -d db
```

### Setup Backend API
1. Navigate to the api folder:
   ```bash
   cd apps/api
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the environment config and adjust as necessary:
   ```bash
   cp ../../.env.example .env
   ```
5. Run migrations/seed the database:
   ```bash
   python seed.py
   ```
6. Run the FastAPI development server:
   ```bash
   uvicorn main:app --reload
   ```

### Setup Frontend UI
1. Navigate to the web folder:
   ```bash
   cd apps/web
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Copy environment configuration:
   ```bash
   cp ../../.env.example .env.local
   ```
4. Run the Next.js dev server:
   ```bash
   npm run dev
   ```
   Open [http://localhost:3000](http://localhost:3000) to view the application.

---

## Sprint 1 Features
- **Project Structure**: Configured Next.js, FastAPI, and docker-compose files.
- **Relational DB Schema**: SQLite default / PostgreSQL models for Users, Resumes, Jobs, Applications, and Audit Logs.
- **Resume Upload**: Endpoint for multipart/form-data upload of resumes.
- **Dashboard UI**: Visual representation of active job applications and resume profiles.
- **Application Tracker**: CRUD operations and list representation for current applications.

## Sprint 2 Features
- **Document Text Extractor**: Integrated real plain-text, PDF (`pypdf`), and Word (`python-docx`) parsing. Unsupported formats are rejected with an HTTP 400.
- **Candidate Profile Database**: Created a dedicated `profiles` table to store verified candidate summaries, metrics, and experience objects.
- **Deterministic Segment Parser**: Scans extracted text to segment experience details, education history, skills, contact info, and metrics.
- **Profile API**: Built endpoints for retrieving, updating, and confirming active candidate profiles.
- **Profile Review Panel**: Developed an interactive dashboard editor tab for editing and locking candidate details.

## Sprint 3.5 Features
- **Deterministic Match Engine**: Formulated a comprehensive matching service that weighs required skills, preferred skills, tools, total years of experience, education degrees, certifications, and soft skills against candidate history.
- **Evidence Finder**: Performs deep keyword audits in profile summary, experience achievements, projects, metrics, and certifications to extract specific textual evidence for each matched skill.
- **Transferable Skills Matrix**: Built mappings for related tech ecosystems (e.g. databases, languages, containers, devops, frontend) to find transferable matches where exact matches are missing.
- **Recommendation & Rationale Engine**: Formulates deterministic recommendations (APPLY/CONSIDER/SKIP) and clear rationales based on alignment score, required skill matches, and experience gaps.
- **Interactive UI Panel**: Created beautiful fit analysis widgets on both Applications tracker and Jobs workspace sidebar to show score progress, rationales, matched evidence, and gaps.
- **Audit Logging Integration**: Logs each run with `fit_analysis_completed` action in `audit_logs` for reporting.
- **Intake Parser Bug Fix**: Fixed a critical frontend routing bug that called the resume parser instead of job parser in the Jobs Intake sidebar.

## Sprint 4 Features
- **Model-Agnostic AI Provider Abstraction**: Created a unified `AIProvider` base class with concrete implementations for a `MockProvider` (simulating response structures locally) and a `GeminiProvider` stub (integrates with the Google GenAI SDK behind the `GEMINI_API_KEY` flag).
- **Prompt Registry with Versioning**: Implemented a version-controlled, centralized `PromptRegistry` class that houses system and user prompt instructions for tasks like `extract_requirements`, `tailor_resume`, and `generate_cover_letter`.
- **JSON Schema Output Validation**: The `ai_orchestrator` parses raw LLM text into JSON and validates it against Pydantic schemas (e.g. `JobParsedData`), preventing downstream format errors and raising `AIValidationError` on failures.
- **AI Audit Logging**: Commits request metadata, prompts, versions, provider, model names, latency (in ms), validations, and error traces as transactions in the `audit_logs` table (action name `ai_request`).
- **Modular Guardrails Service**: Integrated a modular input/output validation framework. Added `ProfileAlignmentGuardrail` to block hallucinations of unsupported skills (such as "Kubernetes") when they are absent from the verified profile, raising `GuardrailViolation` and logging the blocked state.
- **Evaluation Harness**: Created a skeleton evaluation harness (`eval_harness.py`) to run structured prompt regression testing and calculate structure/accuracy pass-rates.
- **Protected Dev Endpoint**: Created a development-only POST endpoint `/analysis/test-ai` protected by the environment flag `ENABLE_DEV_AI_ENDPOINTS=true` (disabled by default) to allow testing the AI Layer.

## Sprint 5 Features
- **Evidence-Based Resume Suggestions**: Implemented orchestrated tailoring recommendations via the AI Layer that compares confirmed profiles to parsed job requirements and deterministically executes matching rationale and evidence mapping.
- **Relational Suggestions Table**: Added the `ai_suggestions` table storing generated suggestions, target requirements, original/suggested text differences, evidence mappings, confidence metrics, and approval states.
- **Status Lifecycle State Machine**: Tracks suggestion approval status (`PENDING`, `APPROVED`, `REJECTED`, `EDITED`) allowing granular candidates reviews.
- **Custom Suggestions Review UI**: Built an interactive reviewer in the Jobs Workspace displaying side-by-side original/suggested text changes, rationales, editable suggestion textareas, and one-click status controls.
- **Dynamic Mocking Provider**: Updated `MockProvider` to dynamically construct tailored suggestions from the prompt's `profile_json` and job description, ensuring dynamic testing is schema-compliant.
- **Suggestions Audit Trails**: Inserts records in `audit_logs` tracking suggestion generation (`suggestions_generated`) and subsequent user approvals (`suggestion_approved`, `suggestion_rejected`, `suggestion_edited`).

## Sprint 6 Features
- **Relational Resume Versions Table**: Added the `resume_versions` table storing base resume IDs, job IDs, created timestamps, active/draft status flags, content JSON representations, and generated markdown representations.
- **Traceable Composition Engine**: Combines the confirmed candidate profile and approved/edited suggestions to construct tailored resumes while enforcing bullet-level traceability mapping back to original text, suggestion IDs, and verified evidence.
- **Active Version Enforcer**: Restricts candidates to one `ACTIVE` version per job. Activating a resume version sets all other versions for the same job to `INACTIVE`.
- **Application Workflow Status Tracking**: Keeps track of application workflow status (`SUGGESTIONS_REVIEWED`, `RESUME_VERSION_CREATED`, `RESUME_VERSION_ACTIVE`) throughout the tailoring process.
- **Visual Diff Comparison Workspace**: Built a side-by-side split pane layout in the frontend comparing the original master resume details against the compiled resume version, highlighting line-level changes.
- **Composition Audit Logging**: Records `resume_version_created`, `resume_version_deleted`, and `resume_version_activated` actions to database audit logs.

## Release 0.1 Hardening Features
- **Authentication & User Isolation**: Integrated real JWT authentication and password hashing. Replaced mock user behavior with private beta accounts. All database queries for resumes, profiles, jobs, applications, suggestions, and resume versions are filtered by `current_user.id` to guarantee secure user data isolation.
- **Guided Empty-State Onboarding**: Replaced empty dashboards with a step-by-step checklist guiding candidates from resume upload to final tailored resume composition.
- **Double-Submit Prevention**: Enforced state-wide action loaders and disabled all inputs and buttons during active backend operations.
- **Synonym Guardrail Allowance**: Updated `ProfileAlignmentGuardrail` to map tech synonyms (e.g., JS ↔ JavaScript, Postgres ↔ PostgreSQL, TS ↔ TypeScript, Node ↔ Node.js, ReactJS ↔ React) to prevent false positive blocks.
- **Feedback Collection Widget**: Added a client feedback collection card to the sidebar, letting private beta users submit ratings and comments to `POST /feedback` (saved to the database, retrieve GET route protected by `ENABLE_DEV_ADMIN_ENDPOINTS=true`).
- **Telemetry Event Tracking**: Added a lightweight event tracking utility to log critical user actions (resume uploads, profile confirmations, suggestions generation, resume creation, and downloads) for product analytics.
- **Lightweight Resume Export**: Added "Download Markdown" and "Copy to Clipboard" utilities to the Tailored Resumes workspace for easy export.
- **Private Beta Notice Banners**: Highlighted the beta state of the app with warnings reminding users to verify all AI-generated content before use.
