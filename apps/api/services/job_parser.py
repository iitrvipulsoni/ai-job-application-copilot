import re
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status

# Re-use skills list for dictionary matching
from services.parser import COMMON_SKILLS

RED_FLAG_KEYWORDS = {
    "rockstar": "Ninja/Rockstar culture (frequently associated with poor work-life balance and high burnout rates)",
    "ninja": "Ninja/Rockstar culture (frequently associated with poor work-life balance and high burnout rates)",
    "fast-paced": "Fast-paced environment (often implies constant urgency, high pressure, or lack of structured processes)",
    "many hats": "Wear many hats (often signals poor role definition, understaffing, or excessive workload)",
    "competitive salary": "Mentions 'competitive salary' without transparent ranges (low compensation transparency)",
    "unpaid": "Mentions 'unpaid' terms (possible exploitation or low-budget constraints)",
    "flexible hours": "Mentions 'flexible hours' (sometimes used to justify 24/7 availability expectations)",
    "work hard play hard": "Work hard, play hard (frequently correlates with mandatory social activities and overtime expectations)"
}

def capitalize_skill(word: str) -> str:
    """
    Formally formats skill names to respect camelCase/uppercase standard notation.
    """
    word_lower = word.lower()
    mapping = {
        "typescript": "TypeScript",
        "javascript": "JavaScript",
        "fastapi": "FastAPI",
        "postgresql": "PostgreSQL",
        "next.js": "Next.js",
        "react": "React",
        "sql": "SQL",
        "css": "CSS",
        "html": "HTML",
        "aws": "AWS",
        "gcp": "GCP",
        "api": "API",
        "ci/cd": "CI/CD",
        "docker": "Docker",
        "kubernetes": "Kubernetes",
        "git": "Git",
        "github": "GitHub",
        "prisma": "Prisma",
        "sqlalchemy": "SQLAlchemy"
    }
    return mapping.get(word_lower, word.title())

def parse_job_description(
    title: str,
    company: str,
    location: Optional[str],
    description: str
) -> dict:
    """
    Deterministically parses job descriptions.
    Extracts experience numbers, required/preferred skills, tools, and red flags.
    Rejects empty job descriptions with HTTP 400.
    """
    if not description or not description.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description cannot be empty."
        )

    # 1. Years of experience extraction (regex scan)
    # Matches patterns like: 3+ years, 5 years, 3 to 5 years, 3-5 years, 3 yrs
    years_experience = None
    exp_matches = re.findall(r'(\d+)\s*\+?\s*(?:-|to)?\s*\d*\s*(?:years?|yrs?)\b', description.lower())
    if exp_matches:
        try:
            # Pick the lowest integer as the minimum requirement
            years_experience = min(int(x) for x in exp_matches)
        except ValueError:
            pass

    # 2. Seniority estimate based on title and description
    seniority = "Mid-Level" # default fallback
    combined_title_desc = (title + " " + description).lower()
    if "junior" in combined_title_desc or "jr" in combined_title_desc:
        seniority = "Junior"
    elif "lead" in combined_title_desc or "principal" in combined_title_desc:
        if "principal" in combined_title_desc:
            seniority = "Principal"
        else:
            seniority = "Lead"
    elif "senior" in combined_title_desc or "sr" in combined_title_desc or (years_experience and years_experience >= 5):
        seniority = "Senior"

    # 3. Employment type check
    employment_type = "Full-time"
    if "part-time" in combined_title_desc or "part time" in combined_title_desc:
        employment_type = "Part-time"
    elif "contract" in combined_title_desc or "contractor" in combined_title_desc:
        employment_type = "Contract"
    elif "intern" in combined_title_desc or "internship" in combined_title_desc:
        employment_type = "Internship"

    # 4. Responsibilities extraction
    # Deterministic scan: find paragraphs starting with bullet marks in "responsibilities" context
    responsibilities = []
    lines = [line.strip() for line in description.split("\n") if line.strip()]
    
    in_resp_section = False
    for line in lines:
        lower_line = line.lower()
        if "responsibilit" in lower_line or "what you will do" in lower_line or "role description" in lower_line:
            in_resp_section = True
            continue
        if in_resp_section and len(line.split()) < 4 and any(header in lower_line for header in ["requirements", "skills", "qualifications", "education"]):
            in_resp_section = False
            
        if in_resp_section and (line.startswith("-") or line.startswith("*") or line.startswith("•")):
            responsibilities.append(line.lstrip("-*• ").strip())

    # 5. Skills & Tools extraction
    required_skills = []
    preferred_skills = []
    tools = []
    domain_keywords = []
    
    # Predefined tools categorizations
    tool_keywords = {"docker", "kubernetes", "git", "github", "aws", "gcp", "azure", "ci/cd", "prisma", "sqlalchemy"}
    domain_matchers = {"saas", "fintech", "ai", "machine learning", "cloud", "security", "web3", "e-commerce"}

    # Heuristic: split description by "preferred" or "nice to have" tags
    desc_parts = re.split(r'\b(preferred|nice\s+to\s+have|pluses|bonus|plus|desirable)\b', description.lower())
    
    required_text = desc_parts[0]
    preferred_text = "".join(desc_parts[1:]) if len(desc_parts) > 1 else ""

    # Detect skills/tools from required segment
    for word in re.findall(r'[a-zA-Z0-9#\+\-\.]+', required_text):
        cleaned_word = word.rstrip(".,")
        if cleaned_word in COMMON_SKILLS:
            capitalized = capitalize_skill(cleaned_word)
            if cleaned_word in tool_keywords:
                if capitalized not in tools:
                    tools.append(capitalized)
            else:
                if capitalized not in required_skills:
                    required_skills.append(capitalized)

    # Detect skills/tools from preferred segment
    for word in re.findall(r'[a-zA-Z0-9#\+\-\.]+', preferred_text):
        cleaned_word = word.rstrip(".,")
        if cleaned_word in COMMON_SKILLS:
            capitalized = capitalize_skill(cleaned_word)
            if cleaned_word in tool_keywords:
                if capitalized not in tools:
                    tools.append(capitalized)
            elif capitalized not in required_skills and capitalized not in preferred_skills:
                preferred_skills.append(capitalized)

    # Extract Domain Keywords
    for domain in domain_matchers:
        if domain in combined_title_desc:
            domain_keywords.append(domain.upper())

    # 6. Education Requirements
    education_requirements = None
    edu_match = re.search(r'\b(bachelor|master|phd|degree|computer\s+science|diploma)\b', combined_title_desc)
    if edu_match:
        if "bachelor" in combined_title_desc:
            education_requirements = "Bachelor's Degree in Computer Science or related"
        elif "master" in combined_title_desc:
            education_requirements = "Master's Degree in Computer Science or related"
        elif "degree" in combined_title_desc:
            education_requirements = "College Degree required"
        else:
            education_requirements = "Degree or equivalent experience required"

    # 7. Certifications
    certifications = []
    if "aws" in combined_title_desc:
        if "aws certified" in combined_title_desc or "solutions architect" in combined_title_desc:
            certifications.append("AWS Solutions Architect or equivalent")

    # 8. Soft Skills
    soft_skills_map = {
        "communication": "Effective Communication",
        "teamwork": "Collaborative Team Player",
        "collaborate": "Collaborative Team Player",
        "problem solving": "Analytical Problem Solving",
        "leadership": "Technical Leadership",
        "mentor": "Mentorship Capabilities",
        "agile": "Agile Methodologies Experience"
    }
    soft_skills = []
    for term, val in soft_skills_map.items():
        if term in combined_title_desc and val not in soft_skills:
            soft_skills.append(val)

    # 9. Red flags scanning
    red_flags = []
    for kw, val in RED_FLAG_KEYWORDS.items():
        if kw in combined_title_desc:
            red_flags.append(val)

    return {
        "company": company,
        "title": title,
        "location": location,
        "seniority": seniority,
        "employment_type": employment_type,
        "responsibilities": responsibilities,
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "tools": tools,
        "domain_keywords": domain_keywords,
        "years_experience": years_experience,
        "education_requirements": education_requirements,
        "certifications": certifications,
        "soft_skills": soft_skills,
        "red_flags": red_flags,
        "raw_job_text": description
    }
