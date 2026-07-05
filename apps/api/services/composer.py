import copy
from typing import List, Dict, Any
from models import AISuggestion, Profile, Resume, Job

def compile_markdown_resume(data: Dict[str, Any]) -> str:
    md = []
    md.append(f"# {data.get('name', 'Candidate Name')}\n")
    
    contact = []
    if data.get("email"): contact.append(data.get("email"))
    if data.get("phone"): contact.append(data.get("phone"))
    if data.get("location"): contact.append(data.get("location"))
    if contact:
        md.append(" | ".join(contact) + "\n")
        
    if data.get("summary"):
        md.append("## Professional Summary")
        md.append(data.get("summary") + "\n")
        
    if data.get("work_experience"):
        md.append("## Work Experience")
        for exp in data.get("work_experience", []):
            md.append(f"### {exp.get('role')} - {exp.get('company')} ({exp.get('duration')})")
            for ach in exp.get("achievements", []):
                md.append(f"* {ach}")
            md.append("")
            
    if data.get("skills"):
        md.append("## Skills")
        md.append(", ".join(data.get("skills", [])) + "\n")
        
    if data.get("tools"):
        md.append("## Tools & Technologies")
        md.append(", ".join(data.get("tools", [])) + "\n")
        
    if data.get("projects"):
        md.append("## Projects")
        for proj in data.get("projects", []):
            md.append(f"### {proj.get('name')}")
            md.append(proj.get('description', ''))
            md.append("")
            
    if data.get("certifications"):
        md.append("## Certifications")
        for cert in data.get("certifications", []):
            md.append(f"* {cert}")
        md.append("")
        
    return "\n".join(md)

def compose_tailored_resume(
    base_resume: Resume,
    profile: Profile,
    approved_suggestions: List[AISuggestion],
    job: Job
) -> Dict[str, Any]:
    """
    Apply APPROVED and EDITED suggestions to the confirmed candidate profile,
    keeping unmodified sections intact, and tracking bullet-level traceability.
    """
    # Clone the confirmed profile's profile_json to avoid side-effects
    content_json = copy.deepcopy(profile.profile_json)
    
    # Initialize traceability mapping
    traceability = {}
    
    # Map suggestions by section and original text for fast lookup
    # Only suggestions with APPROVED or EDITED status are applied
    sug_map = {}
    for sug in approved_suggestions:
        if sug.status in ["APPROVED", "EDITED"]:
            # Store by original text to match specific achievements/bullets
            sug_map[(sug.section, sug.original_text)] = sug

    # 1. Tailor Summary Section
    summary_key = ("Summary", content_json.get("summary", ""))
    summary_skills_key = ("Summary / Skills", content_json.get("summary", ""))
    
    matching_sug = sug_map.get(summary_key) or sug_map.get(summary_skills_key)
    if matching_sug:
        content_json["summary"] = matching_sug.suggested_text
        traceability[str(matching_sug.id)] = {
            "section": "Summary",
            "original_text": matching_sug.original_text,
            "suggested_text": matching_sug.suggested_text,
            "suggestion_id": str(matching_sug.id),
            "evidence": matching_sug.evidence
        }

    # 2. Tailor Work Experience Achievements
    for exp in content_json.get("work_experience", []):
        company = exp.get("company", "")
        role = exp.get("role", "")
        achievements = exp.get("achievements", [])
        new_achievements = []
        
        for ach in achievements:
            # We match on section: "Experience - {company}" or similar, and match original achievement text
            exp_sec_keys = [
                f"Experience - {company}",
                f"Experience: {company}",
                f"{role} - {company}",
                "Experience",
                company
            ]
            
            applied = False
            for sec_key in exp_sec_keys:
                sug_key = (sec_key, ach)
                if sug_key in sug_map:
                    matching_sug = sug_map[sug_key]
                    new_achievements.append(matching_sug.suggested_text)
                    traceability[str(matching_sug.id)] = {
                        "section": sec_key,
                        "original_text": matching_sug.original_text,
                        "suggested_text": matching_sug.suggested_text,
                        "suggestion_id": str(matching_sug.id),
                        "evidence": matching_sug.evidence
                    }
                    applied = True
                    break
            
            if not applied:
                new_achievements.append(ach)
                
        exp["achievements"] = new_achievements

    # 3. Tailor Skills and Tools Sections
    # We can match on "Skills & Tools", "Skills", or "Tools"
    skills_list = content_json.get("skills", [])
    skills_sug_key = ("Skills & Tools", "Skills: " + ", ".join(skills_list[:3]))
    if skills_sug_key in sug_map:
        matching_sug = sug_map[skills_sug_key]
        # In mock suggestion, suggested_text format: "Skills: Python, FastAPI, Docker (Familiar)"
        # We can extract the skills array back out by parsing or just replace it
        if "Skills: " in matching_sug.suggested_text:
            parsed_skills = [s.strip() for s in matching_sug.suggested_text.replace("Skills: ", "").split(",")]
            content_json["skills"] = parsed_skills
            traceability[str(matching_sug.id)] = {
                "section": "Skills & Tools",
                "original_text": matching_sug.original_text,
                "suggested_text": matching_sug.suggested_text,
                "suggestion_id": str(matching_sug.id),
                "evidence": matching_sug.evidence
            }

    # Store traceability details inside the json root
    content_json["_traceability"] = traceability
    
    # Generate markdown
    content_markdown = compile_markdown_resume(content_json)
    
    return {
        "content_json": content_json,
        "content_markdown": content_markdown
    }
