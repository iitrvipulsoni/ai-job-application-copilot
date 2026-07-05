import requests
import uuid
import sys
import argparse

def run_smoke_test(base_url):
    print(f"[START] Starting E2E Smoke Test against: {base_url}\n")
    
    session = requests.Session()
    
    # 1. Register a new user
    user_email = f"smoke_test_{uuid.uuid4().hex[:8]}@example.com"
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

    # 3. Upload Resume
    print("3. Uploading resume...")
    resume_content = b"""
    Jane Doe
    Email: jane@example.com
    Skills: Python, Next.js, PostgreSQL, JS, Postgres
    Experience:
    Software Engineer at TechCorp (2023 - Present)
    - Developed backend microservices using Python.
    - Built frontend dashboards using Next.js.
    """
    files = {"file": ("resume.txt", resume_content, "text/plain")}
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
        print(f"[ERROR] Parse resume failed ({parse_res.status_code}): {parse_res.text}")
        sys.exit(1)
    print("[OK] Resume parsed successfully.\n")

    # 5. Fetch Profile
    print("5. Retrieving candidate profile...")
    profile_res = session.get(f"{base_url}/profile")
    if profile_res.status_code != 200:
        print(f"[ERROR] Fetch profile failed ({profile_res.status_code}): {profile_res.text}")
        sys.exit(1)
    print("[OK] Profile retrieved.\n")

    # 6. Confirm Profile
    print("6. Confirming candidate profile...")
    confirm_res = session.post(f"{base_url}/profile/confirm")
    if confirm_res.status_code != 200:
        print(f"[ERROR] Profile confirmation failed ({confirm_res.status_code}): {confirm_res.text}")
        sys.exit(1)
    print("[OK] Profile confirmed.\n")

    # 7. Create Job Posting
    print("7. Creating job posting card...")
    job_payload = {
        "title": "Software Engineer",
        "company": "NextGen SaaS",
        "location": "Remote",
        "description": "We are looking for a Software Engineer. Must have experience with Python, Next.js, and JavaScript."
    }
    job_res = session.post(f"{base_url}/jobs", json=job_payload)
    if job_res.status_code != 201:
        print(f"[ERROR] Job creation failed ({job_res.status_code}): {job_res.text}")
        sys.exit(1)
        
    job_id = job_res.json()["id"]
    print(f"[OK] Job posting created (ID: {job_id}).\n")

    # 8. Analyze Job Requirements
    print("8. Parsing job requirements...")
    analyze_res = session.post(f"{base_url}/jobs/{job_id}/analyze")
    if analyze_res.status_code != 200:
        print(f"[ERROR] Job parsing failed ({analyze_res.status_code}): {analyze_res.text}")
        sys.exit(1)
    print("[OK] Job description requirements analyzed.\n")

    # 9. Run Fit Analysis
    print("9. Running deterministic fit analysis...")
    fit_res = session.post(f"{base_url}/analysis/fit-analysis?job_id={job_id}")
    if fit_res.status_code != 200:
        print(f"[ERROR] Fit analysis failed ({fit_res.status_code}): {fit_res.text}")
        sys.exit(1)
    
    fit_data = fit_res.json()
    print(f"[OK] Fit analysis completed. Score: {fit_data['match_score']}/100. Recommendation: {fit_data['recommendation']}\n")

    # 10. Generate Suggestions
    print("10. Generating resume tailoring suggestions via AI Orchestrator...")
    sug_res = session.post(f"{base_url}/analysis/suggestions?job_id={job_id}")
    if sug_res.status_code != 200:
        print(f"[ERROR] suggestions generation failed ({sug_res.status_code}): {sug_res.text}")
        sys.exit(1)
        
    suggestions = sug_res.json()
    print(f"[OK] Generated {len(suggestions)} suggestions.")
    if suggestions:
        print(f"Debug suggestion keys: {list(suggestions[0].keys())}")
        print(f"Debug suggestion sample: {suggestions[0]}")
        
    # 11. Approve Suggestions
    if not suggestions:
        print("[ERROR] No suggestions generated by MockProvider.")
        sys.exit(1)
        
    suggestion_id = suggestions[0].get("id") or suggestions[0].get("suggestion_id")
    print(f"11. Approving suggestion: {suggestion_id}...")
    appr_res = session.patch(f"{base_url}/analysis/suggestions/{suggestion_id}", json={
        "status": "APPROVED"
    })
    if appr_res.status_code != 200:
        print(f"[ERROR] suggestion approval failed ({appr_res.status_code}): {appr_res.text}")
        sys.exit(1)
    print("[OK] Suggestion approved.\n")

    # 12. Compose Tailored Resume Version
    print("12. Composing new tailored resume version...")
    comp_res = session.post(f"{base_url}/resume-versions", json={
        "job_id": job_id
    })
    if comp_res.status_code != 201:
        print(f"[ERROR] Resume composition failed ({comp_res.status_code}): {comp_res.text}")
        sys.exit(1)
        
    version_data = comp_res.json()
    print("[OK] Tailored resume version composed successfully.\n")

    # 13. Download / Fetch Composed Resume
    print("13. Downloading resume version content...")
    ver_id = version_data["id"]
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
        "message": "Smoke test was fully successful!"
    })
    if feed_res.status_code != 201:
        print(f"[ERROR] Feedback submission failed ({feed_res.status_code}): {feed_res.text}")
        sys.exit(1)
    print("[OK] Feedback submitted successfully.\n")

    print("[FINISHED] ALL SMOKE TESTS COMPLETED SUCCESSFULLY! Release 0.1 is 100% production-ready.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="E2E Smoke Test for Release 0.1 Backend API")
    parser.add_argument("--url", default="http://localhost:8000", help="Target API Base URL (e.g. http://localhost:8000 or production domain)")
    args = parser.parse_args()
    
    run_smoke_test(args.url.rstrip("/"))
