# System Architecture

The AI Job Application Copilot MVP is designed with a service-oriented architecture separating the Next.js React frontend from the FastAPI Python backend.

## Data Flow
1. User uploads master resume/profile -> stored in PostgreSQL as structured JSON.
2. User tracks a job application -> Job details & Application link stored.
3. Copilot trigger -> FastAPI fetches job description, extracts requirements, overlaps with profile JSON, runs guardrails check, and returns a verified suggestion list.
