import os
import json
from abc import ABC, abstractmethod
from typing import Optional, Type, List, Any
from pydantic import BaseModel

class AIProvider(ABC):
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_schema: Optional[Type[BaseModel]] = None,
        model_name: Optional[str] = None
    ) -> str:
        """
        Executes text generation and returns raw response string.
        """
        pass

# MockProvider generate method
class MockProvider(AIProvider):
    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_schema: Optional[Type[BaseModel]] = None,
        model_name: Optional[str] = None
    ) -> str:
        # Check for specific prompt task overrides
        if "invalid_json_trigger" in prompt:
            # Deliberately return invalid JSON format to test validation blockers
            return "{"

        # If response_schema is ResumeSuggestionsResponse, return dynamic suggestions based on prompt variables
        if response_schema and response_schema.__name__ == "ResumeSuggestionsResponse":
            profile_json = {}
            try:
                if "Candidate Profile:\n" in prompt:
                    json_str = prompt.split("Candidate Profile:\n")[1].split("\nJob Description:\n")[0].strip()
                    profile_json = json.loads(json_str)
            except Exception:
                pass

            if not profile_json:
                profile_json = {"skills": ["Python", "FastAPI"], "work_experience": []}

            skills = profile_json.get("skills", [])
            tools = profile_json.get("tools", [])
            work_exp = profile_json.get("work_experience", [])

            job_title = "Target Position"
            if "Job Title:" in prompt:
                try:
                    job_title = prompt.split("Job Title:")[1].split("\n")[0].strip()
                except:
                    pass

            suggestions = []
            
            # 1. Skill highlight
            if skills:
                primary_skill = skills[0]
                suggestions.append({
                    "suggestion_id": "sug-1",
                    "section": "Summary",
                    "original_text": "Experienced developer skilled in various technologies.",
                    "suggested_text": f"Results-driven Developer with demonstrated expertise in {primary_skill} and building robust web applications.",
                    "suggestion_type": "SKILL_HIGHLIGHT",
                    "target_requirement": f"Required Skill: {primary_skill}",
                    "rationale": f"Emphasizes your core strength in {primary_skill} to align directly with the target job requirements.",
                    "evidence": f"Candidate profile includes {primary_skill} under verified skills list.",
                    "evidence_status": "SUPPORTED",
                    "confidence": 0.95,
                    "requires_user_approval": True
                })

            # 2. Work experience role alignment
            if work_exp:
                exp = work_exp[0]
                role = exp.get("role", "Developer")
                company = exp.get("company", "Previous Employer")
                achievements = exp.get("achievements", [])
                original_ach = achievements[0] if achievements else "Developed code."
                suggestions.append({
                    "suggestion_id": "sug-2",
                    "section": f"Experience - {company}",
                    "original_text": original_ach,
                    "suggested_text": f"{original_ach.rstrip('.')}, contributing to core engineering deliverables aligned with {job_title} duties.",
                    "suggestion_type": "ROLE_ALIGNMENT",
                    "target_requirement": f"Job Title Alignment: {job_title}",
                    "rationale": f"Links your achievements at {company} to the target role of {job_title}.",
                    "evidence": f"Worked as {role} at {company} ({exp.get('duration', 'N/A')}). Achievements list: '{original_ach}'",
                    "evidence_status": "SUPPORTED",
                    "confidence": 0.88,
                    "requires_user_approval": True
                })

            # 3. Weak evidence tool highlight (requires user confirmation)
            if "docker" in prompt.lower() and "docker" not in [s.lower() for s in skills] and "docker" not in [t.lower() for t in tools]:
                suggestions.append({
                    "suggestion_id": "sug-docker",
                    "section": "Skills & Tools",
                    "original_text": "Skills: " + ", ".join(skills[:3]),
                    "suggested_text": "Skills: " + ", ".join(skills[:3]) + ", Docker (Familiar)",
                    "suggestion_type": "TOOL_HIGHLIGHT",
                    "target_requirement": "Preferred Tool: Docker",
                    "rationale": "The job description prefers Docker. Highlighting familiarity if you have basic exposure is recommended.",
                    "evidence": "No explicit Docker skill in profile, but you may have basic familiarity from previous deployment activities.",
                    "evidence_status": "REQUIRES_USER_CONFIRMATION",
                    "confidence": 0.5,
                    "requires_user_approval": True
                })

            # 4. Gap check
            if "kubernetes" in prompt.lower() and "kubernetes" not in [s.lower() for s in skills] and "kubernetes" not in [t.lower() for t in tools]:
                suggestions.append({
                    "suggestion_id": "sug-k8s",
                    "section": "Gaps",
                    "original_text": "",
                    "suggested_text": "",
                    "suggestion_type": "GAP_NOT_CLAIMED",
                    "target_requirement": "Required Tool: Kubernetes",
                    "rationale": "Kubernetes is required but not documented in your candidate profile. We leave this requirement missing to preserve truthfulness.",
                    "evidence": "No evidence of Kubernetes in candidate profile.",
                    "evidence_status": "GAP_NOT_CLAIMED",
                    "confidence": 1.0,
                    "requires_user_approval": True
                })

            # 5. Guardrail violation test case trigger
            if "trigger_kubernetes_violation" in prompt:
                suggestions.append({
                    "suggestion_id": "sug-violation",
                    "section": "Summary",
                    "original_text": "Developer",
                    "suggested_text": "Kubernetes Developer",
                    "suggestion_type": "SKILL_HIGHLIGHT",
                    "target_requirement": "Kubernetes",
                    "rationale": "Testing violation",
                    "evidence": "Fake evidence",
                    "evidence_status": "SUPPORTED",
                    "confidence": 1.0,
                    "requires_user_approval": True
                })

            mock_response = {
                "job_id": "00000000-0000-0000-0000-000000000000",
                "suggestions": suggestions
            }
            return json.dumps(mock_response)

        # If response_schema is provided, generate a mock JSON dictionary that validates against it
        if response_schema:
            mock_data = {}
            for field_name, field in response_schema.model_fields.items():
                annotation = field.annotation
                if annotation == str:
                    if "skill" in field_name.lower():
                        mock_data[field_name] = "Python"
                    elif "reason" in field_name.lower() or "rationale" in field_name.lower():
                        mock_data[field_name] = "Candidate has strong matching criteria."
                    elif "content" in field_name.lower() or "letter" in field_name.lower():
                        mock_data[field_name] = "Dear Hiring Team,\n\nI am writing to express my interest...\n\nSincerely,\nJane Doe"
                    elif "text" in field_name.lower():
                        mock_data[field_name] = "Seeded resume text details."
                    elif "company" in field_name.lower():
                        mock_data[field_name] = "DataScale Systems"
                    elif "title" in field_name.lower():
                        mock_data[field_name] = "Backend API Developer"
                    else:
                        mock_data[field_name] = "mock_string_value"
                elif annotation == int or annotation == Optional[int]:
                    mock_data[field_name] = 3
                elif annotation == float:
                    mock_data[field_name] = 85.0
                elif annotation == bool:
                    mock_data[field_name] = True
                elif getattr(annotation, "__origin__", None) is list or getattr(annotation, "__origin__", None) is List:
                    item_type = annotation.__args__[0]
                    if item_type == str:
                        if "required" in field_name.lower() or "skill" in field_name.lower():
                            mock_data[field_name] = ["Python", "FastAPI", "PostgreSQL"]
                        elif "tool" in field_name.lower():
                            mock_data[field_name] = ["Docker", "SQLAlchemy"]
                        else:
                            mock_data[field_name] = ["item_1", "item_2"]
                    elif issubclass(item_type, BaseModel):
                        nested_mock = {}
                        for n_name, n_field in item_type.model_fields.items():
                            nested_mock[n_name] = "mock_nested_value" if n_field.annotation == str else 1
                        mock_data[field_name] = [nested_mock]
                    else:
                        mock_data[field_name] = []
                elif issubclass(annotation, BaseModel):
                    nested_mock = {}
                    for n_name, n_field in annotation.model_fields.items():
                        nested_mock[n_name] = "mock_nested_value" if n_field.annotation == str else 1
                    mock_data[field_name] = nested_mock
                else:
                    mock_data[field_name] = None
            
            return json.dumps(mock_data)
        
        # If no schema, return generic mock text
        if "invalid_json_trigger" in prompt:
            return "{"
        return "This is a mock text generation response."

class GeminiProvider(AIProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.genai = genai
        except ImportError:
            raise ImportError(
                "google-generativeai package is not installed. Please run pip install google-generativeai"
            )

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_schema: Optional[Type[BaseModel]] = None,
        model_name: Optional[str] = None
    ) -> str:
        model_name = model_name or "gemini-2.5-flash"
        
        generation_config = {}
        if response_schema:
            generation_config["response_mime_type"] = "application/json"
            generation_config["response_schema"] = response_schema

        model = self.genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction,
            generation_config=generation_config
        )
        
        response = model.generate_content(prompt)
        return response.text
