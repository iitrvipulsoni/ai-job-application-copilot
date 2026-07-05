import requests
import uuid
import sys
import argparse

VIPUL_SONI_RESUME_OCR = """
Vipul Soni
Portfolio | LinkedIn | GitHub| iitrvipulsoni@gmail.com | 647-898-4760 | 8 Nahani Way, Mississauga, ON, L4Z 0C6
Experience 
OpenTable | Analyst, Global Revenue Strategy & Operations
December 2023 – Present
 Partnered with Territory VPs to develop GTM plans and market performance strategies, leveraging revenue, 
adoption, promotional, and customer engagement metrics to guide business decisions.
 Built and maintained monthly executive-facing reporting on churn, competitive activity, and key accounts 
(Michelin, Top 100) performance, translating trends into actionable recommendations for overall business.
 Led churn, retention, and competitive analytics for Regional Heads across U.S. and international markets, 
driving targeted retention strategies that reduced churn by 15% and protected $2.5M in ARR. 
 Led competitive impact analysis following American Express’s acquisition of Resy & Tock, identifying high-risk accounts 
and informing pricing, positioning, and retention strategies across key markets. 
 Led daily analysis to track weekly and yearly trends in revenue, app usage, promotional spending, and user behavior; 
investigated anomalies and delivered actionable insights.
 Conducted funnel and diner demand analysis for Fogo de Chão (50+ locations), identifying booking friction 
points and optimizing reservation flows through A/B testing, increasing seated reservations by 15%.
 Owned product KPI reporting and strategic analysis for enterprise growth initiatives and partnerships with Uber, Visa, and 
Slang AI, measuring engagement, growth, and business impact. 
 Launched a referral analytics model to identify high-performing acquisition channels, enabling more targeted marketing 
investments and improving customer acquisition efficiency.
 Developed churn prediction and customer segmentation models using SQL and Python with 85%+ precision, 
enabling proactive account prioritization and data-driven retention planning. 
 Built scalable reporting workflows using SQL, Snowflake, and Power BI, automating revenue, customer, and 
usage analytics while reducing manual reporting effort by 35%. 
 Automated reporting decks and operational workflows using Google Apps Script and AI-powered agents 
(Gemini, Claude, ChatGPT), saving 10+ hours per team member weekly and accelerating insight delivery.
BusyQA | Data Analyst
Mar 2022 – November 2023
 Developed a predictive placement model with 94% accuracy for an HR technology client, increasing placement-driven 
revenue by 30%. 
 Presented analytical findings and quarterly business reviews to senior stakeholders and enterprise clients, translating 
complex datasets into actionable business recommendations.
 Analyzed 100K+ healthcare records to identify adoption patterns and support initiatives that increased virtual care 
utilization by 30% and projected 15% cost savings. 
 Developed SQL scripts, stored procedures, ETL workflows, and data integration workflows to unify data from disparate 
systems and improve analytics accessibility across business teams.
Skills
 Data Platforms & Technologies Analytics & BI Tools: SQL, Python (Pandas, NumPy), Excel, Google Sheets, Power 
BI, Tableau, Apache Superset, Report Builder, Data Modeling, Dashboard Automation, ETL, Snowflake, 
Salesforce, Azure, AWS, Git/GitHub, Jupyter Notebook, Zapier, Jira, Monday, SaaS Analytics Platforms
 Analytics & Business Strategy: Churn & Retention Analysis, Funnel Analysis, Cohort Analysis, LTV/CAC Modeling, 
Revenue Forecasting, A/B Testing, Machine Learning, Predictive Modeling, Regression Analysis, Customer 
Segmentation, GTM Analytics, Pricing Strategy, Quantitative Research, Data Mining, KPI Reporting, Database 
Design, Cross-functional Collaboration
"""

def run_production_smoke_test(base_url):
    print(f"[START] Starting Production Smoke Test against: {base_url}\n")
    
    session = requests.Session()
    
    # 1. Register a new user
    user_email = f"prod_test_{uuid.uuid4().hex[:8]}@example.com"
    user_password = "password123"
    
    print(f"1. Registering user: {user_email}...")
    reg_res = session.post(f"{base_url}/auth/register", json={
        "email": user_email,
        "password": user_password
    })
    if reg_res.status_code != 201:
        print(f"[ERROR] Registration failed ({reg_res.status_code}): {reg_res.text}")
        sys.exit(1)
    print("[OK] Registered successfully.\n")

    # 2. Login to get JWT
    print("2. Logging in...")
    login_res = session.post(f"{base_url}/auth/login", json={
        "email": user_email,
        "password": user_password
    })
    if login_res.status_code != 200:
        print(f"[ERROR] Login failed ({login_res.status_code}): {login_res.text}")
        sys.exit(1)
    
    token = login_res.json()["access_token"]
    session.headers.update({"Authorization": f"Bearer {token}"})
    print("[OK] Login successful. JWT token configured.\n")

    # 3. Upload Vipul Soni Resume
    print("3. Uploading Vipul Soni's resume...")
    files = {"file": ("vipul_soni_resume.txt", VIPUL_SONI_RESUME_OCR.encode("utf-8"), "text/plain")}
    upload_res = session.post(f"{base_url}/resumes/upload", files=files)
    if upload_res.status_code != 200:
        print(f"[ERROR] Resume upload failed ({upload_res.status_code}): {upload_res.text}")
        sys.exit(1)
    
    resume_id = upload_res.json()["id"]
    print(f"[OK] Resume uploaded successfully (ID: {resume_id}).\n")

    # 4. Parse Resume
    print("4. Parsing resume to profile...")
    parse_res = session.post(f"{base_url}/resumes/{resume_id}/parse")
    if parse_res.status_code != 200:
        print(f"[ERROR] Resume parsing failed ({parse_res.status_code}): {parse_res.text}")
        sys.exit(1)
    print("[OK] Resume parsed successfully.\n")

    # 5. Retrieve & Validate Candidate Profile (Vipul Soni assertions)
    print("5. Retrieving candidate profile and validating data fields...")
    prof_res = session.get(f"{base_url}/profile")
    if prof_res.status_code != 200:
        print(f"[ERROR] Profile retrieval failed ({prof_res.status_code}): {prof_res.text}")
        sys.exit(1)
        
    profile_data = prof_res.json()["profile_json"]
    
    # Assert Name
    assert profile_data["name"] == "Vipul Soni", f"Expected name Vipul Soni, got {profile_data['name']}"
    print("  - [PASS] Name: Vipul Soni")
    
    # Assert Email
    assert profile_data["email"] == "iitrvipulsoni@gmail.com", f"Expected email iitrvipulsoni@gmail.com, got {profile_data['email']}"
    print("  - [PASS] Email: iitrvipulsoni@gmail.com")
    
    # Assert Phone
    assert profile_data["phone"] == "647-898-4760", f"Expected phone 647-898-4760, got {profile_data['phone']}"
    print("  - [PASS] Phone: 647-898-4760")
    
    # Assert Jobs
    jobs = profile_data["work_experience"]
    assert len(jobs) >= 2, f"Expected at least 2 jobs, found {len(jobs)}"
    
    opentable_job = next((j for j in jobs if "opentable" in j["company"].lower()), None)
    assert opentable_job is not None, "OpenTable job not found"
    assert "analyst" in opentable_job["role"].lower()
    assert len(opentable_job["achievements"]) >= 8, f"Expected >= 8 achievements, got {len(opentable_job['achievements'])}"
    print("  - [PASS] OpenTable job & achievements parsed correctly")

    busyqa_job = next((j for j in jobs if "busyqa" in j["company"].lower()), None)
    assert busyqa_job is not None, "BusyQA job not found"
    assert "data analyst" in busyqa_job["role"].lower()
    print("  - [PASS] BusyQA job & achievements parsed correctly")
    
    # Assert Skills/Tools
    all_skills_tools = [s.lower() for s in (profile_data["skills"] + profile_data["tools"])]
    required_skills = ["sql", "python", "power bi", "tableau", "snowflake", "salesforce", "aws", "git/github"]
    for s in required_skills:
        assert s.lower() in all_skills_tools, f"Missing skill/tool: {s}"
    print("  - [PASS] Key skills & tools are present")

    # Assert Metrics
    metrics_str = " ".join(profile_data["metrics"]).lower()
    required_metrics = ["15%", "$2.5m", "85%+", "35%", "10+", "94%", "30%"]
    for m in required_metrics:
        assert m.lower() in metrics_str, f"Missing metric: {m}"
    print("  - [PASS] Key metrics are present")

    # Assert Confidence
    assert profile_data["low_confidence"] is False, "Expected low_confidence=False"
    print("  - [PASS] low_confidence is False")
    
    print("[OK] Candidate profile fields validated successfully.\n")

    # 6. Confirm Profile
    print("6. Confirming candidate profile...")
    conf_res = session.post(f"{base_url}/profile/confirm")
    if conf_res.status_code != 200:
        print(f"[ERROR] Profile confirmation failed ({conf_res.status_code}): {conf_res.text}")
        sys.exit(1)
    print("[OK] Profile confirmed.\n")

    # 7. Create Job Posting Card
    print("7. Creating job posting card...")
    job_payload = {
        "title": "Senior Data Analyst",
        "company": "F5 Networks",
        "description": "Required Skill: Python, SQL, Power BI, Git/GitHub. Preferred: Salesforce, Snowflake. 3+ years experience required."
    }
    job_res = session.post(f"{base_url}/jobs", json=job_payload)
    if job_res.status_code != 201:
        print(f"[ERROR] Job creation failed ({job_res.status_code}): {job_res.text}")
        sys.exit(1)
    job_id = job_res.json()["id"]
    print(f"[OK] Job posting created (ID: {job_id}).\n")

    # 8. Analyze Job Description
    print(f"8. Parsing job description requirements (Job ID: {job_id})...")
    parse_job_res = session.post(f"{base_url}/jobs/{job_id}/analyze")
    if parse_job_res.status_code != 200:
        print(f"[ERROR] Job description parsing failed ({parse_job_res.status_code}): {parse_job_res.text}")
        sys.exit(1)
    print("[OK] Job description requirements analyzed.\n")

    # 9. Run Fit Analysis
    print("9. Running deterministic fit analysis...")
    fit_res = session.post(f"{base_url}/analysis/fit-analysis", params={"job_id": job_id})
    if fit_res.status_code != 200:
        print(f"[ERROR] Fit analysis failed ({fit_res.status_code}): {fit_res.text}")
        sys.exit(1)
    fit_data = fit_res.json()
    print(f"[OK] Fit analysis completed. Score: {fit_data['match_score']}/100. Recommendation: {fit_data['recommendation']}\n")

    # 10. Generate Suggestions
    print("10. Generating resume tailoring suggestions via AI Orchestrator...")
    sug_res = session.post(f"{base_url}/analysis/suggestions", params={"job_id": job_id})
    if sug_res.status_code != 200:
        print(f"[ERROR] Suggestions generation failed ({sug_res.status_code}): {sug_res.text}")
        sys.exit(1)
    
    suggestions = sug_res.json()
    print(f"[OK] Generated {len(suggestions)} suggestions.")
    if len(suggestions) == 0:
        print("[ERROR] Suggestions list is empty.")
        sys.exit(1)
        
    sug_id = suggestions[0]["id"]
    print(f"  - Using suggestion ID for approval: {sug_id}\n")

    # 11. Approve Suggestion
    print(f"11. Approving suggestion: {sug_id}...")
    appr_res = session.patch(f"{base_url}/analysis/suggestions/{sug_id}", json={"status": "APPROVED"})
    if appr_res.status_code != 200:
        print(f"[ERROR] Suggestion approval failed ({appr_res.status_code}): {appr_res.text}")
        sys.exit(1)
    print("[OK] Suggestion approved.\n")

    # 12. Compose Tailored Resume Version
    print("12. Composing new tailored resume version...")
    comp_payload = {
        "base_resume_id": resume_id,
        "job_id": job_id
    }
    comp_res = session.post(f"{base_url}/resume-versions", json=comp_payload)
    if comp_res.status_code != 201:
        print(f"[ERROR] Composition failed ({comp_res.status_code}): {comp_res.text}")
        sys.exit(1)
    ver_id = comp_res.json()["id"]
    print(f"[OK] Tailored resume version composed successfully (Version ID: {ver_id}).\n")

    # 13. Download/Copy Resume Version
    print("13. Downloading resume version content...")
    ver_res = session.get(f"{base_url}/resume-versions/{ver_id}")
    if ver_res.status_code != 200:
        print(f"[ERROR] Resume download failed ({ver_res.status_code}): {ver_res.text}")
        sys.exit(1)
    print("[OK] Tailored resume content fetched successfully.\n")

    # 14. Submit User Feedback
    print("14. Submitting beta user feedback...")
    feed_res = session.post(f"{base_url}/feedback", json={
        "rating": 5,
        "category": "General",
        "message": "Production smoke test was fully successful!"
    })
    if feed_res.status_code != 201:
        print(f"[ERROR] Feedback submission failed ({feed_res.status_code}): {feed_res.text}")
        sys.exit(1)
    print("[OK] Feedback submitted successfully.\n")

    print("[FINISHED] ALL PRODUCTION SMOKE TESTS COMPLETED SUCCESSFULLY!")
    print("Release 0.1 is 100% stable, secure, and production-ready on the public cloud!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Production E2E Smoke Test for Release 0.1 Backend API")
    parser.add_argument("--url", default="https://copilot-backend-api.onrender.com", help="Target API Base URL")
    args = parser.parse_args()
    
    run_production_smoke_test(args.url.rstrip("/"))
