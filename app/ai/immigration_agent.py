import os
import re
import json
from typing import Any, Dict
from datetime import datetime, date

from crewai import Agent, Task, Crew, Process, LLM
from app.ai.immigration_ocr_tool import landingai_ocr_extract_immigration_fields

DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')

def run_immigration_extraction_crew(file_path: str) -> Dict[str, Any]:
    """
    Extract immigration profile data from a document using CrewAI agent.
    Returns structured data that can be used to update a user's profile.
    """
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required.")

    model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    llm = LLM(model=model, api_key=openrouter_api_key, base_url="https://openrouter.ai/api/v1")

    agent = Agent(
        role="Immigration Document Extractor",
        goal="Extract and validate immigration profile data from documents reliably.",
        backstory=(
            "You extract structured data from immigration documents (passports, permits, degrees, etc.). "
            "You always call the extraction tool first, then normalize/validate its output. "
            "You identify the document type and extract relevant fields. You never guess missing data."
        ),
        tools=[landingai_ocr_extract_immigration_fields],
        llm=llm,
        verbose=True,
    )

    task = Task(
        description=(
            f"You must extract immigration profile information from this document: {file_path}\n\n"
            f"CRITICAL: You MUST use this exact file_path: {file_path}\n\n"
            "Steps:\n"
            "1) Call the tool landingai_ocr_extract_immigration_fields with the file_path.\n"
            "2) Read tool_output.fields to get extracted data.\n"
            "3) Normalize and validate:\n"
            "   - Dates: Ensure YYYY-MM-DD format\n"
            "   - Strings: Strip whitespace, capitalize appropriately\n"
            "   - JSON fields: Ensure valid JSON structure\n"
            "4) Identify document_type from content if not extracted\n"
            "5) Output STRICT JSON ONLY with double quotes:\n"
            '{\n'
            '  "status": "completed" or "partial",\n'
            '  "document_type": "passport|study_permit|work_permit|degree|language_test|work_reference|other",\n'
            '  "fields": {\n'
            '    "dob": "YYYY-MM-DD" or null,\n'
            '    "citizenship": string or null,\n'
            '    "province": string or null,\n'
            '    "city": string or null,\n'
            '    "arrival_date": "YYYY-MM-DD" or null,\n'
            '    "education": {...} or null,\n'
            '    "language_tests": {...} or null,\n'
            '    "work_experience": {...} or null\n'
            '  },\n'
            '  "reason": "explain what was extracted or what is missing"\n'
            '}\n'
            "Do not include any extra text outside JSON."
        ),
        expected_output="A strict JSON object with status, document_type, fields, and reason.",
        agent=agent,
    )

    crew = Crew(process=Process.sequential, agents=[agent], tasks=[task])
    result = crew.kickoff(inputs={"file_path": file_path})

    raw = result.raw if hasattr(result, "raw") else str(result)

    # Parse JSON robustly
    try:
        data = json.loads(raw)
    except Exception:
        return {
            "status": "partial",
            "document_type": "unknown",
            "fields": {},
            "reason": "Agent returned non-JSON output",
            "raw": raw,
        }

    # Validate and normalize dates
    fields = data.get("fields") or {}
    
    for date_field in ["dob", "arrival_date"]:
        date_val = fields.get(date_field)
        if date_val:
            # Try to validate date format
            if not DATE_RE.match(str(date_val)):
                fields[date_field] = None
                data["reason"] = (data.get("reason") or "") + f" Invalid {date_field} format."

    data["fields"] = fields
    return data
