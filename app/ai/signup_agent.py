import os
import re
import json
from typing import Any, Dict

from crewai import Agent, Task, Crew, Process, LLM
from app.ai.ocr_tool import landingai_ocr_extract_signup_fields

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def run_signup_extraction_crew(file_path: str) -> Dict[str, Any]:
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required.")

    model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")  # common OpenRouter style
    llm = LLM(model=model, api_key=openrouter_api_key, base_url="https://openrouter.ai/api/v1")

    agent = Agent(
        role="Document Signup Extractor",
        goal="Extract and validate name/email/age from signup document reliably.",
        backstory=(
            "You always call the extraction tool first, then normalize/validate its output. "
            "If any field is missing/invalid, you set status=needs_review. You never guess."
        ),
        tools=[landingai_ocr_extract_signup_fields],
        llm=llm,
        verbose=True,   # turn on while debugging
    )

    task = Task(
        description=(
            f"You must extract signup information from this document: {file_path}\n\n"
            f"CRITICAL: You MUST use this exact file_path: {file_path}\n\n"
            "Steps:\n"
            "1) Call the tool landingai_ocr_extract_signup_fields with the file_path.\n"
            "2) Read tool_output.fields.name/email/age.\n"
            "3) Normalize:\n"
            "   - name: strip extra spaces\n"
            "   - email: lowercase + strip\n"
            "   - age: integer\n"
            "4) Validate:\n"
            "   - email matches a normal email pattern\n"
            "   - age is between 0 and 120\n"
            "5) Output STRICT JSON ONLY with double quotes:\n"
            '{\n'
            '  "status": "completed" or "needs_review",\n'
            '  "fields": {"name": string|null, "email": string|null, "age": number|null},\n'
            '  "reason": "explain what is missing/invalid or why completed"\n'
            '}\n'
            "Do not include any extra text outside JSON."
        ),
        expected_output="A strict JSON object with status, fields, and reason.",
        agent=agent,
    )

    crew = Crew(process=Process.sequential, agents=[agent], tasks=[task])
    result = crew.kickoff(inputs={"file_path": file_path})

    raw = result.raw if hasattr(result, "raw") else str(result)

    # Parse JSON robustly
    try:
        data = json.loads(raw)
    except Exception:
        # fallback: return needs_review with raw attached
        return {
            "status": "needs_review",
            "fields": {"name": None, "email": None, "age": None},
            "reason": "Agent returned non-JSON output",
            "raw": raw,
        }

    # Optional deterministic validation pass (recommended)
    fields = data.get("fields") or {}
    email = (fields.get("email") or "").strip().lower()
    age = fields.get("age")

    if email and not EMAIL_RE.match(email):
        data["status"] = "needs_review"
        data["reason"] = (data.get("reason") or "") + " Invalid email format."

    if age is not None:
        try:
            age_int = int(age)
            fields["age"] = age_int
            if age_int < 0 or age_int > 120:
                data["status"] = "needs_review"
                data["reason"] = (data.get("reason") or "") + " Age out of range."
        except Exception:
            data["status"] = "needs_review"
            data["reason"] = (data.get("reason") or "") + " Age not an integer."

    data["fields"] = fields
    return data
