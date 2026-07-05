import os
import sys
import pytest

# Add the apps/api folder to python path for importing modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/api")))

from services.parser import parse_resume_text

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

def test_vipul_resume_parser():
    parsed = parse_resume_text(VIPUL_SONI_RESUME_OCR)

    # 1. Contact details validation
    assert parsed["name"] == "Vipul Soni"
    assert parsed["email"] == "iitrvipulsoni@gmail.com"
    assert parsed["phone"] == "647-898-4760"

    # 2. Jobs extraction validation
    jobs = parsed["work_experience"]
    assert len(jobs) >= 2, f"Expected at least 2 jobs, found {len(jobs)}"
    
    # Verify OpenTable job
    opentable_job = next((j for j in jobs if "opentable" in j["company"].lower()), None)
    assert opentable_job is not None, "OpenTable job not found"
    assert "analyst" in opentable_job["role"].lower()
    assert "global revenue strategy" in opentable_job["role"].lower()
    assert "december 2023" in opentable_job["duration"].lower()
    assert "present" in opentable_job["duration"].lower()
    assert len(opentable_job["achievements"]) >= 8, f"Expected at least 8 OpenTable achievements, found {len(opentable_job['achievements'])}"

    # Verify BusyQA job
    busyqa_job = next((j for j in jobs if "busyqa" in j["company"].lower()), None)
    assert busyqa_job is not None, "BusyQA job not found"
    assert "data analyst" in busyqa_job["role"].lower()
    assert "mar 2022" in busyqa_job["duration"].lower()
    assert "november 2023" in busyqa_job["duration"].lower()

    # 3. Skills validation
    # Normalize skills/tools combined list for assertion
    all_skills_tools = [s.lower() for s in (parsed["skills"] + parsed["tools"])]
    required_skills = ["sql", "python", "power bi", "tableau", "snowflake", "salesforce", "aws", "git/github"]
    for s in required_skills:
        assert s.lower() in all_skills_tools, f"Missing skill/tool: {s}"

    # 4. Metrics validation
    metrics_str = " ".join(parsed["metrics"]).lower()
    required_metrics = ["15%", "$2.5m", "85%+", "35%", "10+", "94%", "30%"]
    for m in required_metrics:
        assert m.lower() in metrics_str, f"Missing metric assertion value: {m}"

    # 5. Low confidence check (should be false since all core components are successfully parsed)
    assert parsed["low_confidence"] is False
