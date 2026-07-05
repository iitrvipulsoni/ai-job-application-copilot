import os
import re
from typing import Dict, List, Any, Tuple
from fastapi import HTTPException, status
import pypdf
import docx

# A basic list of common technology keywords to extract skills/tools
COMMON_SKILLS = {
    "python", "javascript", "typescript", "react", "next.js", "vue", "angular", "node.js",
    "fastapi", "flask", "django", "express", "postgresql", "mysql", "mongodb", "sqlite",
    "sql", "nosql", "sqlalchemy", "prisma", "docker", "kubernetes", "aws", "gcp", "azure",
    "git", "github", "html", "css", "sass", "tailwind", "bootstrap", "ci/cd", "jest",
    "cypress", "pytest", "numpy", "pandas", "scikit-learn", "tensorflow", "pytorch",
    "java", "c++", "c#", "go", "rust", "ruby", "php"
}

def extract_text_from_file(file_path: str, file_name: str) -> str:
    """
    Validates file extension and extracts raw text.
    Supports .txt, .md, .pdf, and .docx. Rejects others with a 400 HTTP exception.
    """
    ext = os.path.splitext(file_name)[1].lower()
    
    if ext in [".txt", ".md"]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to read text file: {str(e)}"
            )
            
    elif ext == ".pdf":
        try:
            reader = pypdf.PdfReader(file_path)
            pages_text = []
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    pages_text.append(t)
            return "\n".join(pages_text)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to parse PDF file: {str(e)}"
            )
            
    elif ext == ".docx":
        try:
            doc = docx.Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs]
            # Also extract table text to avoid missing info
            table_text = []
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        table_text.append(cell.text)
            return "\n".join(paragraphs + table_text)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to parse DOCX file: {str(e)}"
            )
            
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Only .txt, .md, .pdf, and .docx are supported."
        )

def parse_resume_text(text: str) -> dict:
    """
    Deterministic rule-based parser.
    Extracts contact info via regex, segments sections by scanning headers,
    and groups lists using basic text splits. Avoids hallucinating missing information.
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    # 1. Regex parsing for contact details
    email = None
    email_match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
    if email_match:
        email = email_match.group(0)
        
    phone = None
    # Matches +1-555-555-5555, (555) 555-5555, 555.555.5555, etc.
    phone_match = re.search(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
    if phone_match:
        phone = phone_match.group(0)
        
    # Attempt to extract location (City, ST or City, Country)
    location = None
    loc_match = re.search(r'([A-Za-z\s]+),\s*([A-Z]{2}|[A-Za-z]{4,15})', text)
    if loc_match:
        location = loc_match.group(0)

    # Attempt to extract name (First non-empty line that doesn't contain email/phone, max 4 words)
    name = ""
    for line in lines[:5]:
        if email and email in line:
            continue
        if phone and phone in line:
            continue
        if len(line.split()) <= 4 and not re.search(r'\b(resume|cv|curriculum)\b', line.lower()):
            name = line
            break

    # 2. Section Segmentation
    sections = _split_sections(lines)
    
    # Summary
    summary = ""
    summary_lines = sections.get("summary", [])
    if summary_lines:
        summary = " ".join(summary_lines)
        
    # Experience
    work_experience = []
    exp_lines = sections.get("experience", [])
    if exp_lines:
        # Group experiences by looking for company/role/dates patterns or bullet points
        work_experience = _parse_experience_sections(exp_lines)
        
    # Education
    education = []
    edu_lines = sections.get("education", [])
    if edu_lines:
        education = _parse_education_sections(edu_lines)

    # Projects
    projects = []
    project_lines = sections.get("projects", [])
    if project_lines:
        projects = _parse_projects_sections(project_lines)

    # Skills & Tools: keyword match
    skills = []
    tools = []
    
    # Comma split in skills section if present, fallback to global keyword scanning
    skills_section_lines = sections.get("skills", [])
    skills_text = " ".join(skills_section_lines).lower()
    
    # Separate skills from tools based on keyword categories
    detected_keywords = []
    for word in re.findall(r'[a-zA-Z0-9#\+\-\.]+', text.lower()):
        if word in COMMON_SKILLS and word not in detected_keywords:
            detected_keywords.append(word)
            
    # Assign matched keywords to skills/tools (Sprint 2 heuristic split)
    tool_keywords = {"docker", "kubernetes", "git", "github", "aws", "gcp", "azure", "ci/cd", "prisma", "sqlalchemy"}
    for kw in detected_keywords:
        # Capitalize appropriately
        capitalized = kw.replace("fastapi", "FastAPI").replace("postgresql", "PostgreSQL").replace("typescript", "TypeScript").replace("javascript", "JavaScript").replace("next.js", "Next.js").replace("sql", "SQL").title()
        if kw in tool_keywords:
            tools.append(capitalized)
        else:
            skills.append(capitalized)

    # Certifications
    certifications = []
    cert_lines = sections.get("certifications", [])
    for line in cert_lines:
        if len(line) > 5 and not line.startswith("-"):
            certifications.append(line)
        elif line.startswith("-") and len(line) > 6:
            certifications.append(line[1:].strip())

    # Achievements
    achievements = []
    ach_lines = sections.get("achievements", [])
    for line in ach_lines:
        if len(line) > 5:
            achievements.append(line.lstrip("- ").strip())

    # Metrics (Extract lines containing percentages, dollar values, or numbers representing increase/decrease)
    metrics = []
    metric_pattern = re.compile(r'(\d+%\s*|\$\d+|\d+\s*(?:years|months|x|million|users|speed|percent))', re.IGNORECASE)
    for line in lines:
        if metric_pattern.search(line) and ("increase" in line.lower() or "decrease" in line.lower() or "optimize" in line.lower() or "save" in line.lower() or "built" in line.lower() or "grow" in line.lower()):
            metrics.append(line.lstrip("- ").strip())

    return {
        "name": name or None,
        "email": email or None,
        "phone": phone or None,
        "location": location or None,
        "summary": summary or None,
        "work_experience": work_experience,
        "education": education,
        "skills": skills,
        "tools": tools,
        "projects": projects,
        "certifications": certifications,
        "achievements": achievements,
        "metrics": metrics
    }

def _split_sections(lines: List[str]) -> Dict[str, List[str]]:
    """
    Groups lines under core sections.
    """
    sections = {}
    current_section = "summary" # Default starting section
    
    # Common headers mapping
    header_mapping = {
        r'\b(experience|work\s+experience|employment|employment\s+history|history)\b': "experience",
        r'\b(education|academic|background)\b': "education",
        r'\b(skills|core\s+skills|technical\s+skills|capabilities)\b': "skills",
        r'\b(projects|personal\s+projects)\b': "projects",
        r'\b(certifications|credentials|licenses)\b': "certifications",
        r'\b(achievements|awards|accomplishments)\b': "achievements",
        r'\b(summary|objective|profile)\b': "summary"
    }
    
    for line in lines:
        is_header = False
        lower_line = line.lower().strip()
        
        # Section headers are usually short (less than 4 words)
        if len(line.split()) <= 4:
            for pattern, sec_name in header_mapping.items():
                if re.match(pattern, lower_line):
                    current_section = sec_name
                    is_header = True
                    break
        
        if is_header:
            continue
            
        if current_section not in sections:
            sections[current_section] = []
        sections[current_section].append(line)
        
    return sections

def _parse_experience_sections(lines: List[str]) -> List[Dict[str, Any]]:
    """
    Parses experience items from text segment lines.
    """
    experiences = []
    current_exp = None
    
    # Regex to detect date ranges (e.g. 2023 - Present, Jan 2020 - Dec 2022, 2021-2024)
    date_pattern = re.compile(r'\b((?:19|20)\d{2}\s*[-–]\s*(?:Present|\d{4}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b))', re.IGNORECASE)
    
    for line in lines:
        has_date = date_pattern.search(line)
        
        # If the line contains a date and is short, it's likely a company/role header line
        if has_date and len(line.split()) < 10:
            if current_exp:
                experiences.append(current_exp)
                
            # Parse company name and role
            # Typical format: Role | Company | Dates or Company - Role - Dates
            parts = [p.strip() for p in re.split(r'[,|–\-\t]', line)]
            role = "Software Engineer" # Fallback
            company = "Company" # Fallback
            duration = has_date.group(0)
            
            non_date_parts = [p for p in parts if not date_pattern.search(p) and p]
            if len(non_date_parts) >= 2:
                role = non_date_parts[0]
                company = non_date_parts[1]
            elif len(non_date_parts) == 1:
                company = non_date_parts[0]
                
            current_exp = {
                "role": role,
                "company": company,
                "duration": duration,
                "achievements": [],
                "source_text": line
            }
        else:
            if current_exp:
                clean_line = line.lstrip("-*• ").strip()
                if clean_line:
                    current_exp["achievements"].append(clean_line)
                    current_exp["source_text"] += "\n" + line
            else:
                # If no experience header detected yet, initialize a generic placeholder
                current_exp = {
                    "role": "Professional Experience",
                    "company": "Company",
                    "duration": "Duration",
                    "achievements": [line.lstrip("-*• ").strip()],
                    "source_text": line
                }
                
    if current_exp:
        experiences.append(current_exp)
        
    return experiences

def _parse_education_sections(lines: List[str]) -> List[Dict[str, Any]]:
    """
    Parses education items from text segment lines.
    """
    education = []
    edu_date_pattern = re.compile(r'\b((?:19|20)\d{2})')
    
    for line in lines:
        if len(line) < 3:
            continue
        
        parts = [p.strip() for p in re.split(r'[,|–\-]', line)]
        degree = "Degree"
        institution = "Institution"
        duration = "Date"
        
        dates = edu_date_pattern.findall(line)
        if dates:
            duration = " - ".join(dates) if len(dates) >= 2 else dates[0]
            
        non_date_parts = [p for p in parts if not edu_date_pattern.search(p) and p]
        if len(non_date_parts) >= 2:
            degree = non_date_parts[0]
            institution = non_date_parts[1]
        elif len(non_date_parts) == 1:
            institution = non_date_parts[0]
            
        education.append({
            "degree": degree,
            "institution": institution,
            "duration": duration,
            "source_text": line
        })
        
    return education

def _parse_projects_sections(lines: List[str]) -> List[Dict[str, Any]]:
    """
    Parses projects from text segment lines.
    """
    projects = []
    current_proj = None
    
    for line in lines:
        # A new project header is detected if it starts with a bullet-less capitalized line
        if not line.startswith("-") and not line.startswith("*") and not line.startswith("•") and len(line) < 40:
            if current_proj:
                projects.append(current_proj)
            current_proj = {
                "name": line.strip(),
                "description": "",
                "source_text": line
            }
        else:
            if current_proj:
                current_proj["description"] += (" " if current_proj["description"] else "") + line.lstrip("-*• ").strip()
                current_proj["source_text"] += "\n" + line
            else:
                current_proj = {
                    "name": "Project Details",
                    "description": line.lstrip("-*• ").strip(),
                    "source_text": line
                }
                
    if current_proj:
        projects.append(current_proj)
        
    return projects
