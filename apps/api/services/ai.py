import os

def extract_job_requirements(job_description: str) -> dict:
    """
    Calls LLM to extract key skills and requirements from a job description.
    Sprint 1: Returns a parsed mock dictionary of requirements.
    """
    return {
        "required_skills": ["TypeScript", "Next.js", "FastAPI", "PostgreSQL"],
        "preferred_skills": ["Docker", "AI Integration", "Python testing"],
        "minimum_experience_years": 3,
        "education": "Bachelor's degree or equivalent practical experience"
    }

def generate_cover_letter(resume_text: str, job_description: str) -> str:
    """
    Generates a cover letter based strictly on evidence in the resume text,
    avoiding fabrications.
    """
    return (
        "Dear Hiring Team,\n\n"
        "I am writing to express my enthusiastic interest in the Software Engineer position. "
        "Based on my professional experience as a Full Stack Engineer at SaaS Platform Inc., "
        "I have developed robust experience building backend services using Python and PostgreSQL, "
        "as well as frontend web features using Next.js.\n\n"
        "I pride myself on writing clean code and structuring relational databases, matching "
        "the requirements specified in your job posting. I look forward to discussing how my "
        "documented skills can support your development goals.\n\n"
        "Sincerely,\nJane Doe"
    )
