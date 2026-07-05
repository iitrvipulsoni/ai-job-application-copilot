import uuid
from datetime import datetime, timezone
from database import SessionLocal, engine, Base
from models import User, Job, Resume, Application, ApplicationStatus, AuditLog, AuditLogStatus, Profile

def seed_db():
    print("Resetting and seeding database...")
    # Recreate tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Create default mock user
        mock_user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
        developer = User(
            id=mock_user_id,
            email="developer@example.com",
            hashed_password="pbkdf2:sha256:600000$mock_hash_for_development"
        )
        db.add(developer)
        db.commit()
        db.refresh(developer)
        print("[OK] Mock developer user seeded.")
        
        # Create default candidate profile
        mock_profile = Profile(
            id=uuid.uuid4(),
            user_id=mock_user_id,
            raw_text="Jane Doe\nEmail: developer@example.com\nPhone: +1-555-0100\nLocation: San Francisco, CA\nSummary: Full Stack Engineer with experience in Python and Next.js.",
            profile_json={
                "name": "Jane Doe",
                "email": "developer@example.com",
                "phone": "+1-555-0100",
                "location": "San Francisco, CA",
                "summary": "Full Stack Engineer with experience in Python and Next.js.",
                "work_experience": [
                    {
                        "role": "Full Stack Engineer",
                        "company": "SaaS Platform Inc.",
                        "duration": "2023 - 2026",
                        "achievements": [
                            "Developed backend microservices using Python and PostgreSQL.",
                            "Replaced legacy styling with performance-optimized CSS modules.",
                            "Maintained security audit trails for regulatory compliance."
                        ],
                        "source_text": "Full Stack Engineer at SaaS Platform Inc. (2023 - 2026)\n- Developed backend microservices using Python and PostgreSQL.\n- Replaced legacy styling with performance-optimized CSS modules.\n- Maintained security audit trails for regulatory compliance."
                    }
                ],
                "education": [
                    {
                        "degree": "B.S. Computer Science",
                        "institution": "Stanford University",
                        "duration": "2019 - 2023",
                        "source_text": "B.S. Computer Science, Stanford University (2019 - 2023)"
                    }
                ],
                "skills": ["TypeScript", "Next.js", "FastAPI", "PostgreSQL", "Python", "SQLAlchemy"],
                "tools": ["Docker", "Git", "GitHub"],
                "projects": [
                    {
                        "name": "Personal Portfolio",
                        "description": "Portfolio website built with Next.js and styled using Vanilla CSS modules.",
                        "source_text": "Personal Portfolio: built with Next.js and styled using Vanilla CSS modules."
                    }
                ],
                "certifications": ["AWS Certified Cloud Practitioner"],
                "achievements": ["Graduated Cum Laude"],
                "metrics": ["Optimized backend query speed by 40%"]
            },
            confirmed=False
        )
        db.add(mock_profile)
        db.commit()
        print("[OK] Mock candidate profile seeded.")
        
        # Create mock jobs
        from services.job_parser import parse_job_description
        
        desc1 = "Looking for a Senior Full-Stack Engineer with 5+ years of experience. Must know Next.js, React, Python, and PostgreSQL. Docker experience is preferred. Responsibilities include building UI dashboards and optimizing database queries."
        parsed_req1 = parse_job_description(
            title="Senior Full-Stack Engineer",
            company="InnovateTech Solutions",
            location="Remote",
            description=desc1
        )
        job1 = Job(
            id=uuid.uuid4(),
            title="Senior Full-Stack Engineer",
            company="InnovateTech Solutions",
            location="Remote",
            description=desc1,
            extracted_requirements=parsed_req1
        )
        
        desc2 = "Looking for a Python Developer experienced in FastAPI, SQLAlchemy, and PostgreSQL. Experience writing robust tests and containerizing applications is a major plus."
        parsed_req2 = parse_job_description(
            title="Backend API Developer",
            company="DataScale Systems",
            location="Chicago, IL",
            description=desc2
        )
        job2 = Job(
            id=uuid.uuid4(),
            title="Backend API Developer",
            company="DataScale Systems",
            location="Chicago, IL",
            description=desc2,
            extracted_requirements=parsed_req2
        )
        db.add_all([job1, job2])
        db.commit()
        db.refresh(job1)
        db.refresh(job2)
        print("[OK] Mock jobs seeded.")
        
        # Create mock applications
        app1 = Application(
            user_id=mock_user_id,
            job_id=job1.id,
            status=ApplicationStatus.SAVED,
            notes="Requires a strong focus on Next.js styling and design system integration."
        )
        
        app2 = Application(
            user_id=mock_user_id,
            job_id=job2.id,
            status=ApplicationStatus.INTERVIEWING,
            notes="Technical screening scheduled for next week.",
            applied_at=datetime.now(timezone.utc)
        )
        db.add_all([app1, app2])
        db.commit()
        print("[OK] Mock applications seeded.")
        
        # Create a sample audit log
        log = AuditLog(
            user_id=mock_user_id,
            action="db_seed",
            status=AuditLogStatus.SUCCESS,
            details={"message": "Initial database seed completed successfully."}
        )
        db.add(log)
        db.commit()
        print("[OK] Mock audit log seeded.")
        
        print("[SUCCESS] Database seeding completed successfully!")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
