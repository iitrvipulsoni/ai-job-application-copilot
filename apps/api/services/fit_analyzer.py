import re

TRANSFERABLE_GROUPS = [
    {"typescript", "javascript", "react", "next.js", "vue", "angular", "html", "css", "sass", "tailwind", "bootstrap"},
    {"python", "fastapi", "django", "flask", "sqlalchemy", "prisma"},
    {"postgresql", "mysql", "sqlite", "mongodb", "sql", "nosql"},
    {"docker", "kubernetes"},
    {"aws", "gcp", "azure"}
]

def parse_total_experience_years(work_experience: list) -> float:
    total_years = 0.0
    for exp in work_experience:
        duration = exp.get("duration", "")
        if not duration:
            continue
        years = [int(y) for y in re.findall(r'\b(19\d{2}|20\d{2})\b', duration)]
        if len(years) >= 2:
            total_years += max(0, years[1] - years[0])
        elif len(years) == 1:
            if any(w in duration.lower() for w in ["present", "current", "now"]):
                total_years += max(0, 2026 - years[0])
            else:
                total_years += 1.0
    return total_years

def find_transferable_match(skill: str, candidate_skills: list) -> str:
    skill_lower = skill.lower()
    for group in TRANSFERABLE_GROUPS:
        if skill_lower in group:
            for cand_skill in candidate_skills:
                if cand_skill.lower() in group and cand_skill.lower() != skill_lower:
                    return cand_skill
    return None

def search_evidence(term: str, profile_json: dict) -> list:
    term_lower = term.lower()
    evidence = []
    
    # 1. Check in skills / tools lists
    if term_lower in [s.lower() for s in profile_json.get("skills", []) or []]:
        evidence.append("Declared in candidate's skills list.")
    if term_lower in [t.lower() for t in profile_json.get("tools", []) or []]:
        evidence.append("Declared in candidate's tools list.")
        
    # 2. Check summary
    summary = profile_json.get("summary", "")
    if summary and term_lower in summary.lower():
        evidence.append(f"Mentioned in summary: \"{summary}\"")
        
    # 3. Check work experience achievements
    for exp in profile_json.get("work_experience", []) or []:
        role = exp.get("role", "Software Engineer")
        company = exp.get("company", "Company")
        duration = exp.get("duration", "")
        if term_lower in role.lower() or term_lower in company.lower():
            evidence.append(f"Used during role as {role} at {company} ({duration}).")
        for ach in exp.get("achievements", []) or []:
            if term_lower in ach.lower():
                evidence.append(f"Experience at {company} ({duration}): \"{ach}\"")
                
    # 4. Check projects
    for proj in profile_json.get("projects", []) or []:
        name = proj.get("name", "Project")
        desc = proj.get("description", "")
        if term_lower in name.lower() or term_lower in desc.lower():
            evidence.append(f"Project '{name}': \"{desc}\"")
            
    # 5. Check certifications
    for cert in profile_json.get("certifications", []) or []:
        if term_lower in cert.lower():
            evidence.append(f"Certification: {cert}")
            
    # 6. Check achievements
    for ach in profile_json.get("achievements", []) or []:
        if term_lower in ach.lower():
            evidence.append(f"Achievement: {ach}")
            
    # 7. Check metrics
    for met in profile_json.get("metrics", []) or []:
        if term_lower in met.lower():
            evidence.append(f"Metric: {met}")
            
    return evidence

def analyze_fit_deterministic(profile_json: dict, extracted_requirements: dict) -> dict:
    strong_matches = []
    partial_matches = []
    missing_requirements = []
    transferable_matches = []
    evidence_map = {}
    
    candidate_skills = profile_json.get("skills", []) or []
    candidate_tools = profile_json.get("tools", []) or []
    candidate_certs = profile_json.get("certifications", []) or []
    
    # 1. Required Skills matching
    req_skills_score = 0.0
    req_skills_total = 0
    required_skills = extracted_requirements.get("required_skills", []) or []
    for skill in required_skills:
        req_skills_total += 1
        evidence = search_evidence(skill, profile_json)
        if evidence:
            strong_matches.append(skill)
            evidence_map[skill] = "; ".join(evidence)
            req_skills_score += 1.0
        else:
            trans_match = find_transferable_match(skill, candidate_skills)
            if trans_match:
                transferable_matches.append({
                    "required": skill,
                    "candidate_has": trans_match
                })
                evidence_map[skill] = f"Candidate has experience with {trans_match}, which is transferable to {skill}."
                req_skills_score += 0.5
            else:
                missing_requirements.append(f"Required Skill: {skill}")
                
    # 2. Tools matching
    tools_score = 0.0
    tools_total = 0
    req_tools = extracted_requirements.get("tools", []) or []
    for tool in req_tools:
        tools_total += 1
        evidence = search_evidence(tool, profile_json)
        if evidence:
            strong_matches.append(tool)
            evidence_map[tool] = "; ".join(evidence)
            tools_score += 1.0
        else:
            trans_match = find_transferable_match(tool, candidate_tools)
            if trans_match:
                transferable_matches.append({
                    "required": tool,
                    "candidate_has": trans_match
                })
                evidence_map[tool] = f"Candidate has experience with {trans_match}, which is transferable to {tool}."
                tools_score += 0.5
            else:
                missing_requirements.append(f"Required Tool: {tool}")
                
    # 3. Preferred Skills matching
    pref_skills_score = 0.0
    pref_skills_total = 0
    pref_skills = extracted_requirements.get("preferred_skills", []) or []
    for skill in pref_skills:
        pref_skills_total += 1
        evidence = search_evidence(skill, profile_json)
        if evidence:
            strong_matches.append(skill)
            evidence_map[skill] = "; ".join(evidence)
            pref_skills_score += 1.0
        else:
            trans_match = find_transferable_match(skill, candidate_skills)
            if trans_match:
                transferable_matches.append({
                    "required": skill,
                    "candidate_has": trans_match
                })
                evidence_map[skill] = f"Candidate has experience with {trans_match}, which is transferable to {skill}."
                pref_skills_score += 0.5
            else:
                missing_requirements.append(f"Preferred Skill: {skill}")

    # 4. Years of experience matching
    years_score = 0.0
    years_total = 0
    req_years = extracted_requirements.get("years_experience")
    if req_years is not None:
        years_total = 1
        candidate_years = parse_total_experience_years(profile_json.get("work_experience", []))
        if candidate_years >= req_years:
            strong_matches.append(f"Experience: {req_years}+ Years")
            evidence_map[f"Experience: {req_years}+ Years"] = f"Candidate has {candidate_years} years of experience, meeting the required {req_years} years."
            years_score = 1.0
        elif candidate_years > 0:
            partial_matches.append(f"Experience: {req_years}+ Years (Have {candidate_years} Years)")
            evidence_map[f"Experience: {req_years}+ Years (Have {candidate_years} Years)"] = f"Candidate has only {candidate_years} years of total experience, which is less than the required {req_years} years."
            years_score = candidate_years / req_years
        else:
            missing_requirements.append(f"Required Experience: {req_years} Years")
            
    # 5. Education matching
    edu_score = 0.0
    edu_total = 0
    req_edu = extracted_requirements.get("education_requirements")
    if req_edu:
        edu_total = 1
        req_edu_lower = req_edu.lower()
        candidate_edus = profile_json.get("education", []) or []
        matched_edu = False
        degree_found = None
        institution_found = None
        for edu in candidate_edus:
            degree = edu.get("degree", "").lower()
            if "bachelor" in req_edu_lower or "b.s." in req_edu_lower or "computer science" in req_edu_lower:
                if any(k in degree for k in ["bachelor", "b.s.", "b.a.", "bs", "ba"]):
                    matched_edu = True
                    degree_found = edu.get("degree")
                    institution_found = edu.get("institution")
                    break
            elif "master" in req_edu_lower:
                if any(k in degree for k in ["master", "m.s.", "m.a.", "ms", "ma", "mba"]):
                    matched_edu = True
                    degree_found = edu.get("degree")
                    institution_found = edu.get("institution")
                    break
            elif "degree" in req_edu_lower:
                if any(k in degree for k in ["degree", "bachelor", "master", "associate", "b.s.", "m.s.", "b.a.", "bs", "ms"]):
                    matched_edu = True
                    degree_found = edu.get("degree")
                    institution_found = edu.get("institution")
                    break
                    
        if matched_edu:
            strong_matches.append("Education: Degree Requirement")
            evidence_map["Education: Degree Requirement"] = f"Candidate has {degree_found} from {institution_found}."
            edu_score = 1.0
        elif candidate_edus:
            degree_found = candidate_edus[0].get("degree")
            institution_found = candidate_edus[0].get("institution")
            partial_matches.append("Education: Degree Requirement (Partial Match)")
            evidence_map["Education: Degree Requirement (Partial Match)"] = f"Candidate has {degree_found} from {institution_found}, which may not fully align with '{req_edu}'."
            edu_score = 0.5
        else:
            missing_requirements.append(f"Required Education: {req_edu}")

    # 6. Certifications matching
    certs_score = 0.0
    certs_total = 0
    req_certs = extracted_requirements.get("certifications", []) or []
    for cert in req_certs:
        certs_total += 1
        cert_lower = cert.lower()
        matched_cert = False
        for c in candidate_certs:
            if cert_lower in c.lower() or c.lower() in cert_lower:
                matched_cert = True
                strong_matches.append(f"Certification: {cert}")
                evidence_map[f"Certification: {cert}"] = f"Candidate holds certification: {c}"
                certs_score += 1.0
                break
        if not matched_cert:
            missing_requirements.append(f"Required Certification: {cert}")
            
    # 7. Soft Skills matching
    soft_score = 0.0
    soft_total = 0
    req_soft = extracted_requirements.get("soft_skills", []) or []
    for s_skill in req_soft:
        soft_total += 1
        evidence = search_evidence(s_skill, profile_json)
        if evidence:
            strong_matches.append(s_skill)
            evidence_map[s_skill] = "; ".join(evidence)
            soft_score += 1.0
        else:
            missing_requirements.append(f"Soft Skill: {s_skill}")

    weights = {
        "required_skills": 35.0,
        "preferred_skills": 10.0,
        "tools": 15.0,
        "years_experience": 15.0,
        "education": 10.0,
        "certifications": 10.0,
        "soft_skills": 5.0
    }
    
    total_weight = 0.0
    earned_weight = 0.0
    
    if req_skills_total > 0:
        total_weight += weights["required_skills"]
        earned_weight += (req_skills_score / req_skills_total) * weights["required_skills"]
        
    if pref_skills_total > 0:
        total_weight += weights["preferred_skills"]
        earned_weight += (pref_skills_score / pref_skills_total) * weights["preferred_skills"]
        
    if tools_total > 0:
        total_weight += weights["tools"]
        earned_weight += (tools_score / tools_total) * weights["tools"]
        
    if years_total > 0:
        total_weight += weights["years_experience"]
        earned_weight += years_score * weights["years_experience"]
        
    if edu_total > 0:
        total_weight += weights["education"]
        earned_weight += edu_score * weights["education"]
        
    if certs_total > 0:
        total_weight += weights["certifications"]
        earned_weight += (certs_score / certs_total) * weights["certifications"]
        
    if soft_total > 0:
        total_weight += weights["soft_skills"]
        earned_weight += (soft_score / soft_total) * weights["soft_skills"]
        
    if total_weight > 0:
        match_score = round((earned_weight / total_weight) * 100)
        
        meets_exp = True
        if req_years is not None:
            candidate_years = parse_total_experience_years(profile_json.get("work_experience", []))
            if candidate_years < req_years:
                meets_exp = False
                
        req_skills_match_ratio = 1.0
        if req_skills_total > 0:
            matched_count = sum(1 for s in required_skills if s in strong_matches)
            req_skills_match_ratio = matched_count / req_skills_total
            
        if match_score >= 80 and meets_exp and req_skills_match_ratio >= 0.70:
            recommendation = "APPLY"
            rationale = f"Strong match score of {match_score}%. Candidate meets required years of experience ({req_years if req_years is not None else 'N/A'} years) and matches {int(req_skills_match_ratio * 100)}% of the core required skills."
        elif match_score >= 50:
            recommendation = "CONSIDER"
            rationale = f"Moderate match score of {match_score}%. Gaps identified in key skills or experience. Candidate matches {int(req_skills_match_ratio * 100)}% of core required skills."
        else:
            recommendation = "SKIP"
            rationale = f"Low alignment score of {match_score}%. Significant mismatch in core required skills ({int(req_skills_match_ratio * 100)}% matched) or years of experience."
    else:
        match_score = 0
        recommendation = "CONSIDER"
        rationale = "No requirements could be extracted from the job description to run a fit analysis. Please verify the job description text."
        
    return {
        "match_score": match_score,
        "strong_matches": strong_matches,
        "partial_matches": partial_matches,
        "missing_requirements": missing_requirements,
        "transferable_matches": transferable_matches,
        "evidence_map": evidence_map,
        "recommendation": recommendation,
        "rationale": rationale
    }
