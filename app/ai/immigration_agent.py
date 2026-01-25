import os
import re
import json
import logging
from typing import Any, Dict
from datetime import datetime, date

from crewai import Agent, Task, Crew, Process, LLM
from app.ai.immigration_ocr_tool import landingai_ocr_extract_immigration_fields

DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')

def extract_json_from_markdown(text: str) -> str:
    """
    Extract JSON from markdown code blocks.
    Handles both ```json and ``` formats.
    """
    if not text:
        return text
    
    text = text.strip()
    
    # Try to find JSON in markdown code blocks
    # Pattern: ```json\n{...}\n``` or ```\n{...}\n```
    # Also handle cases where there might be whitespace before/after or no newline after ```
    code_block_pattern = r'```(?:json)?\s*\n?(.*?)\n?\s*```'
    match = re.search(code_block_pattern, text, re.DOTALL)
    if match:
        extracted = match.group(1).strip()
        # Validate it looks like JSON (starts with { or [)
        if extracted.startswith(('{', '[')):
            return extracted
    
    # If no code block found, try to find JSON object directly
    # Look for { ... } pattern - find the outermost braces
    # This handles nested JSON objects
    brace_count = 0
    start_idx = -1
    for i, char in enumerate(text):
        if char == '{':
            if brace_count == 0:
                start_idx = i
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and start_idx != -1:
                # Found complete JSON object
                json_candidate = text[start_idx:i+1]
                # Quick validation: try to parse it
                try:
                    json.loads(json_candidate)
                    return json_candidate
                except:
                    pass
    
    # If nothing found, return original text (might already be JSON)
    return text

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
        role="CRS Profile Data Extractor",
        goal="Extract all data needed for Express Entry CRS (Comprehensive Ranking System) score calculation from immigration documents.",
        backstory=(
            "You are an expert at extracting CRS-relevant data from immigration documents. "
            "You understand that CRS scores require: age (from DOB), marital status, education level, "
            "language test scores (IELTS/CELPIP/PTE/TEF/TCF with 4 skills), Canadian/foreign work years, "
            "and additional factors (provincial nomination, sibling, certificate of qualification). "
            "You always call the extraction tool first, then normalize/validate its output. "
            "You identify the document type and extract CRS-relevant fields. You never guess missing data."
        ),
        tools=[landingai_ocr_extract_immigration_fields],
        llm=llm,
        verbose=True,  # Enable verbose to see CrewAI logs
    )

    task = Task(
        description=(
            f"You must extract CRS (Comprehensive Ranking System) profile data from this document: {file_path}\n\n"
            f"CRITICAL: You MUST use this exact file_path: {file_path}\n\n"
            "CRS requires these fields for score calculation:\n"
            "- Basic: dob (YYYY-MM-DD), marital_status, citizenship\n"
            "- For passport, study_permit, work_permit: date_of_issue (YYYY-MM-DD), date_of_expiry (YYYY-MM-DD) if present on document\n"
            "- For language tests (ielts, celpip, pte_core, tef_canada, tcf_canada): date_of_issue = test date, "
            "date_of_expiry = 'valid until' / result expiry if on document, else test date + 2 years (IRCC validity)\n"
            "- Education: education_level, education_level_detail, canadian_education (true/false)\n"
            "- Language: language_test_type (ielts/celpip/pte_core/tef_canada/tcf_canada), "
            "language_speaking/listening/reading/writing (numeric scores)\n"
            "- Work: canadian_work_years (0-5+), foreign_work_years (0-3+)\n"
            "- Additional: certificate_of_qualification, provincial_nomination, sibling_in_canada (all true/false)\n"
            "- Spouse (if applicable): spouse_accompanying, spouse_canadian_pr, spouse_education_level, "
            "spouse_canadian_work_years, spouse_language_test_type, spouse_language_speaking/listening/reading/writing\n\n"
            "Steps:\n"
            "1) Call the tool landingai_ocr_extract_immigration_fields with the file_path.\n"
            "2) Read tool_output.fields to get extracted data.\n"
            "3) Normalize and validate:\n"
            "   - Dates: Ensure YYYY-MM-DD format\n"
            "   - Booleans: Convert 'true'/'false' strings to boolean\n"
            "   - Numeric: Ensure years and language scores are numbers\n"
            "   - Test types: Normalize to lowercase (ielts, celpip, pte_core, tef_canada, tcf_canada)\n"
            "4) Identify document_type from content. Common types:\n"
            "   - passport: Contains passport number, MRZ, issuing country, biometric photo\n"
            "   - ielts: Contains 'IELTS', 'International English Language Testing System', test scores, TRF number\n"
            "   - celpip: Contains 'CELPIP', 'Canadian English Language Proficiency Index Program', test scores\n"
            "   - pte_core: Contains 'PTE Core', 'Pearson Test of English', test scores\n"
            "   - tef_canada: Contains 'TEF Canada', 'Test d'évaluation de français', test scores\n"
            "   - tcf_canada: Contains 'TCF Canada', 'Test de connaissance du français', test scores\n"
            "   - language_test: Generic language test if specific type unclear\n"
            "   - degree: University degree, diploma, graduation certificate\n"
            "   - transcript: Academic transcript, marksheet\n"
            "   - study_permit: Canadian study permit document\n"
            "   - work_permit: Canadian work permit document\n"
            "   - work_reference: Employment letter, work experience certificate\n"
            "   - other: If document type cannot be determined\n"
            "5) Output STRICT JSON ONLY with double quotes:\n"
            '{\n'
            '  "status": "completed" or "partial",\n'
            '  "document_type": "passport|ielts|celpip|pte_core|tef_canada|tcf_canada|language_test|study_permit|work_permit|degree|transcript|work_reference|other",\n'
            '  "fields": {\n'
            '    "dob": "YYYY-MM-DD" or null,\n'
            '    "date_of_issue": "YYYY-MM-DD" or null (passport, permit, language test = test date),\n'
            '    "date_of_expiry": "YYYY-MM-DD" or null (passport, permit, language test = valid until or test+2y),\n'
            '    "marital_status": "single|married|common_law|divorced|separated|widowed|annulled" or null,\n'
            '    "education_level": "secondary|one_two_year_diploma|bachelors|masters|phd|two_or_more" or null,\n'
            '    "education_level_detail": string or null,\n'
            '    "canadian_education": true/false or null,\n'
            '    "language_test_type": "ielts|celpip|pte_core|tef_canada|tcf_canada" or null,\n'
            '    "language_speaking": number or null,\n'
            '    "language_listening": number or null,\n'
            '    "language_reading": number or null,\n'
            '    "language_writing": number or null,\n'
            '    "canadian_work_years": number or null,\n'
            '    "foreign_work_years": number or null,\n'
            '    "provincial_nomination": true/false or null,\n'
            '    "sibling_in_canada": true/false or null,\n'
            '    ... (other CRS fields as extracted)\n'
            '  },\n'
            '  "reason": "explain what CRS-relevant data was extracted or what is missing"\n'
            '}\n'
            "Do not include any extra text outside JSON."
        ),
        expected_output="A strict JSON object with status, document_type, fields (CRS-relevant), and reason.",
        agent=agent,
    )

    crew = Crew(process=Process.sequential, agents=[agent], tasks=[task])
    result = crew.kickoff(inputs={"file_path": file_path})

    raw = result.raw if hasattr(result, "raw") else str(result)

    # Extract JSON from markdown code blocks if present
    json_text = extract_json_from_markdown(raw)

    # Parse JSON robustly
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        # If JSON parsing fails, log and return error
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to parse JSON: {e}")
        logger.debug(f"Extracted JSON text: {json_text[:500]}...")
        logger.debug(f"Raw output: {raw[:500]}...")
        return {
            "status": "partial",
            "document_type": "unknown",
            "fields": {},
            "reason": "Agent returned non-JSON output",
            "raw": raw,
        }
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error parsing JSON: {e}")
        return {
            "status": "partial",
            "document_type": "unknown",
            "fields": {},
            "reason": f"Error parsing agent output: {str(e)}",
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
