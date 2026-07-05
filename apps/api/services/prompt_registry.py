from typing import Dict, Tuple

class PromptRegistry:
    def __init__(self):
        # Format: {prompt_id: {version: {"system": str, "user": str}}}
        self._prompts: Dict[str, Dict[str, Dict[str, str]]] = {}
        self._latest_versions: Dict[str, str] = {}
        
        # Seed initial prompts
        self.register_prompt(
            prompt_id="extract_requirements",
            version="1.0.0",
            system_instruction="You are an expert technical recruiter. Extract job requirements into a JSON structure.",
            user_template="Job Title: {title}\nCompany: {company}\nLocation: {location}\nDescription:\n{description}"
        )
        self.register_prompt(
            prompt_id="tailor_resume",
            version="1.0.0",
            system_instruction=(
                "You are an AI career coach. Review the candidate profile and job requirements, "
                "then suggest truthful tailoring additions/changes. Never fabricate experience."
            ),
            user_template="Candidate Profile:\n{profile_json}\nJob Description:\n{job_description}"
        )
        self.register_prompt(
            prompt_id="generate_cover_letter",
            version="1.0.0",
            system_instruction=(
                "You are an AI application writer. Write a customized cover letter. "
                "Use only achievements and skills documented in the verified candidate profile. Do not fabricate."
            ),
            user_template="Candidate Profile:\n{profile_json}\nJob Title: {title}\nCompany: {company}\nDescription:\n{description}"
        )

    def register_prompt(self, prompt_id: str, version: str, system_instruction: str, user_template: str):
        if prompt_id not in self._prompts:
            self._prompts[prompt_id] = {}
        self._prompts[prompt_id][version] = {
            "system": system_instruction,
            "user": user_template
        }
        
        current_latest = self._latest_versions.get(prompt_id)
        if not current_latest or version > current_latest:
            self._latest_versions[prompt_id] = version

    def get_prompt(self, prompt_id: str, version: str = "latest") -> Tuple[str, str, str]:
        """
        Returns Tuple of (system_instruction, user_template, actual_version)
        """
        if prompt_id not in self._prompts:
            raise KeyError(f"Prompt ID '{prompt_id}' not found in registry.")
        
        if version == "latest":
            actual_version = self._latest_versions[prompt_id]
        else:
            actual_version = version

        if actual_version not in self._prompts[prompt_id]:
            raise KeyError(f"Version '{actual_version}' not found for prompt ID '{prompt_id}'.")

        prompt_data = self._prompts[prompt_id][actual_version]
        return prompt_data["system"], prompt_data["user"], actual_version

# Global registry instance
registry = PromptRegistry()
