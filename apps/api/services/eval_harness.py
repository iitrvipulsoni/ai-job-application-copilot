import time
from typing import List, Dict, Any, Type
from pydantic import BaseModel

from services.ai_orchestrator import execute_ai_task
from services.ai_provider import MockProvider

class EvalCase(BaseModel):
    name: str
    prompt_id: str
    input_variables: Dict[str, Any]
    output_schema: Type[BaseModel]
    expected_keywords: List[str]

def run_evaluation(cases: List[EvalCase], provider=None) -> Dict[str, Any]:
    """
    Runs evaluations for prompt/model testing.
    """
    if provider is None:
        provider = MockProvider()

    results = []
    success_count = 0
    total_latency_ms = 0

    print(f"Starting prompt evaluation harness using provider: {provider.__class__.__name__}...")

    for idx, case in enumerate(cases):
        print(f"[{idx+1}/{len(cases)}] Running case: {case.name}...")
        start_time = time.perf_counter()
        
        status = "PASSED"
        error_msg = None
        output = None
        
        try:
            output = execute_ai_task(
                user_id=None,
                task_type="evaluation",
                prompt_id=case.prompt_id,
                input_variables=case.input_variables,
                output_schema=case.output_schema,
                provider=provider,
                db=None
            )
            
            import json
            out_str = json.dumps(output).lower()
            for kw in case.expected_keywords:
                if kw.lower() not in out_str:
                    status = "FAILED"
                    error_msg = f"Expected keyword '{kw}' was missing from the output."
                    break
        except Exception as e:
            status = "FAILED"
            error_msg = str(e)
            
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        total_latency_ms += latency_ms
        
        if status == "PASSED":
            success_count += 1
            
        results.append({
            "case_name": case.name,
            "status": status,
            "latency_ms": latency_ms,
            "error": error_msg,
            "output": output
        })
        
        print(f"    Status: {status} | Latency: {latency_ms}ms" + (f" | Error: {error_msg}" if error_msg else ""))

    summary = {
        "total_cases": len(cases),
        "passed": success_count,
        "failed": len(cases) - success_count,
        "pass_rate": f"{(success_count / len(cases) * 100):.1f}%" if cases else "0%",
        "avg_latency_ms": int(total_latency_ms / len(cases)) if cases else 0,
        "results": results
    }
    
    print("\n--- Evaluation Summary ---")
    print(f"Total Cases: {summary['total_cases']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Pass Rate: {summary['pass_rate']}")
    print(f"Average Latency: {summary['avg_latency_ms']}ms")
    
    return summary

if __name__ == "__main__":
    class DummyRequirementsSchema(BaseModel):
        required_skills: List[str]
        preferred_skills: List[str]
        minimum_experience_years: int
        education: str

    test_cases = [
        EvalCase(
            name="Extract Requirements Mock Test",
            prompt_id="extract_requirements",
            input_variables={
                "title": "Backend Dev",
                "company": "DataScale",
                "location": "Chicago",
                "description": "Must know Python and FastAPI."
            },
            output_schema=DummyRequirementsSchema,
            expected_keywords=["Python", "FastAPI"]
        )
    ]
    run_evaluation(test_cases)
