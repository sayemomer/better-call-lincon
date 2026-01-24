import os
import re
import json
from typing import Any, Dict

from crewai import Agent, Task, Crew, Process, LLM
from app.ai.ocr_tool import landingai_ocr_extract_signup_fields, _extract_signup_fields_impl

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def run_signup_extraction_crew(file_path: str) -> Dict[str, Any]:
    """
    Extract signup information from a passport document.
    First validates that the document is a passport, then extracts name/email/age.
    """
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required.")

    model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    llm = LLM(model=model, api_key=openrouter_api_key, base_url="https://openrouter.ai/api/v1")

    # Agent to validate passport and extract fields
    agent = Agent(
        role="Passport Document Validator and Signup Extractor",
        goal="Validate that the document is a passport, then extract name/email/age from passport for signup.",
        backstory=(
            "You are an expert at identifying passport documents and extracting signup information. "
            "You MUST first verify the document is a passport by checking for passport indicators like: "
            "'PASSPORT', 'PASSEPORT', passport number, issuing country, MRZ (Machine Readable Zone), "
            "biometric photo, passport holder name, date of birth, nationality, etc. "
            "If it's NOT a passport, return status='invalid_document' with reason explaining why. "
            "If it IS a passport, extract name, email (if present), and age (from date of birth). "
            "If email is missing from passport, set status='need_review' so user can provide it. "
            "You always call the extraction tool first, then validate the document type and fields."
        ),
        tools=[landingai_ocr_extract_signup_fields],
        llm=llm,
        verbose=True,
    )

    task = Task(
        description=(
            f"Analyze this document: {file_path}\n\n"
            f"CRITICAL: You MUST use this exact file_path: {file_path}\n\n"
            "STEP 1 - Document Type Validation:\n"
            "1) Call landingai_ocr_extract_signup_fields with the file_path.\n"
            "2) Analyze the extracted content to determine if this is a PASSPORT document.\n"
            "3) Look for passport indicators: 'PASSPORT', 'PASSEPORT', passport number format, "
            "MRZ codes, issuing country/authority, biometric photo area, passport holder fields.\n"
            "4) If NOT a passport, return:\n"
            '   {"status": "invalid_document", "fields": {}, "reason": "Document is not a passport. Only passport documents are accepted for signup."}\n\n'
            "STEP 2 - If it IS a passport, extract ALL passport fields:\n"
            "5) Extract ALL available passport information:\n"
            "   - Basic: surname, given_name, name, dob, citizenship, sex, place_of_birth\n"
            "   - Passport details: passport_number, country_code, personal_number, previous_passport_no\n"
            "   - Dates: date_of_issue, date_of_expiry\n"
            "   - Family: fathers_name, mothers_name, marital_status\n"
            "   - Address: permanent_address\n"
            "   - Travel: travel_history (as JSON array if available)\n"
            "   - Age: calculate from DOB if not directly provided\n"
            "   - Email: usually null (user will provide)\n"
            "6) Normalize all fields:\n"
            "   - names: strip extra spaces, proper case\n"
            "   - dates: format as YYYY-MM-DD\n"
            "   - citizenship/country_code: uppercase\n"
            "   - sex: M or F\n"
            "   - marital_status: lowercase\n"
            "7) Validate critical fields:\n"
            "   - name (or surname+given_name) must be present\n"
            "   - dob must be present and valid date\n"
            "   - citizenship must be present\n"
            "   - passport_number should be present\n"
            "8) Determine status:\n"
            "    - If critical fields (name, dob, citizenship) are valid: status='need_review'\n"
            "    - Email is always provided by user during finalization\n"
            "    - Extract as many fields as possible, even if some are missing\n\n"
            "STEP 3 - Output STRICT JSON ONLY:\n"
            '{\n'
            '  "status": "invalid_document" | "completed" | "need_review",\n'
            '  "fields": {\n'
            '    "surname": string|null, "given_name": string|null, "name": string|null,\n'
            '    "dob": string|null (YYYY-MM-DD), "citizenship": string|null, "sex": string|null,\n'
            '    "place_of_birth": string|null, "passport_number": string|null,\n'
            '    "country_code": string|null, "personal_number": string|null,\n'
            '    "previous_passport_no": string|null, "date_of_issue": string|null (YYYY-MM-DD),\n'
            '    "date_of_expiry": string|null (YYYY-MM-DD), "fathers_name": string|null,\n'
            '    "mothers_name": string|null, "marital_status": string|null,\n'
            '    "permanent_address": string|null, "travel_history": array|null,\n'
            '    "email": string|null, "age": number|null\n'
            '  },\n'
            '  "reason": "explain document type, what was extracted, or what is missing"\n'
            '}\n'
            "Do not include any extra text outside JSON."
        ),
        expected_output="A strict JSON object with status, fields, and reason.",
        agent=agent,
    )

    crew = Crew(process=Process.sequential, agents=[agent], tasks=[task])
    result = crew.kickoff(inputs={"file_path": file_path})

    raw = result.raw if hasattr(result, "raw") else str(result)
    
    # Get raw markdown from OCR tool (call the implementation directly, not the tool wrapper)
    try:
        ocr_result = _extract_signup_fields_impl(file_path)
        ocr_markdown = ocr_result.get("raw", {}).get("markdown", "")
        ocr_extracted = ocr_result.get("raw", {}).get("extracted", {})
    except Exception as e:
        # If OCR fails, continue without it
        print(f"Warning: Failed to get OCR raw data: {str(e)}")
        ocr_markdown = ""
        ocr_extracted = {}

    # Parse JSON robustly - handle markdown code blocks
    data = None
    try:
        # Try direct JSON parse first
        data = json.loads(raw)
    except Exception:
        # Try to extract JSON from markdown code blocks
        import re
        # Look for JSON in code blocks (```json ... ``` or ``` ... ```)
        # Match the entire JSON object including nested braces
        json_match = re.search(r'```(?:json)?\s*(\{(?:[^{}]|(?:\{[^{}]*\}))*\})\s*```', raw, re.DOTALL)
        if json_match:
            try:
                json_str = json_match.group(1)
                data = json.loads(json_str)
            except Exception:
                pass
        
        # If still no data, try to find JSON object in the text (more robust pattern)
        if not data:
            # Find the first { and try to match balanced braces
            start_idx = raw.find('{')
            if start_idx != -1:
                brace_count = 0
                end_idx = start_idx
                for i in range(start_idx, len(raw)):
                    if raw[i] == '{':
                        brace_count += 1
                    elif raw[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break
                if brace_count == 0:
                    try:
                        json_str = raw[start_idx:end_idx]
                        data = json.loads(json_str)
                    except Exception:
                        pass
    
    if not data:
        # fallback: return need_review with raw attached
        return {
            "status": "need_review",
            "fields": {"name": None, "email": None, "age": None},
            "reason": "Agent returned non-JSON output. Please review manually.",
            "raw": raw,
            "ocr_markdown": ocr_markdown,
            "ocr_extracted": ocr_extracted,
        }
    
    # Add OCR raw data to response
    data["ocr_markdown"] = ocr_markdown
    data["ocr_extracted"] = ocr_extracted

    # Additional validation
    status = data.get("status", "need_review")
    fields = data.get("fields") or {}
    
    # If invalid document, return early
    if status == "invalid_document":
        return data
    
    # Validate critical fields (name, dob, citizenship)
    name = (fields.get("name") or "").strip()
    surname = (fields.get("surname") or "").strip()
    given_name = (fields.get("given_name") or "").strip()
    
    # If name not provided, try to construct from surname/given_name
    if not name:
        if surname and given_name:
            name = f"{given_name} {surname}".strip()
            fields["name"] = name
        elif surname:
            name = surname
            fields["name"] = name
        elif given_name:
            name = given_name
            fields["name"] = name
    
    if not name:
        data["status"] = "need_review"
        data["reason"] = (data.get("reason") or "") + " Name not found in passport."
    
    # Validate DOB
    dob_str = fields.get("dob")
    if not dob_str:
        data["status"] = "need_review"
        data["reason"] = (data.get("reason") or "") + " Date of birth not found in passport."
    else:
        # Validate DOB format
        try:
            from datetime import datetime
            dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            fields["dob"] = dob_str  # Keep as string for JSON serialization
        except (ValueError, TypeError):
            data["status"] = "need_review"
            data["reason"] = (data.get("reason") or "") + " Invalid date of birth format."
            fields["dob"] = None
    
    # Validate citizenship
    citizenship = (fields.get("citizenship") or "").strip()
    if not citizenship:
        data["status"] = "need_review"
        data["reason"] = (data.get("reason") or "") + " Citizenship not found in passport."
        fields["citizenship"] = None
    
    # Validate email format if present
    email = (fields.get("email") or "").strip().lower()
    if email and not EMAIL_RE.match(email):
        data["status"] = "need_review"
        data["reason"] = (data.get("reason") or "") + " Invalid email format."
        fields["email"] = None

    # Validate age
    age = fields.get("age")
    if age is not None:
        try:
            age_int = int(age)
            fields["age"] = age_int
            if age_int < 0 or age_int > 120:
                data["status"] = "need_review"
                data["reason"] = (data.get("reason") or "") + " Age out of range."
        except Exception:
            data["status"] = "need_review"
            data["reason"] = (data.get("reason") or "") + " Age not an integer."
            fields["age"] = None

    # Final check: If email is missing, status MUST be need_review (email is always required from user)
    # This check MUST override any status returned by the agent if email is missing
    # Re-check email from fields (it might have been set to None earlier during validation)
    final_email = (fields.get("email") or "").strip()
    if not final_email or final_email.lower() == "null" or final_email == "":
        # Force status to need_review if email is missing - this overrides any "completed" status
        data["status"] = "need_review"
        reason = data.get("reason") or ""
        if "email" not in reason.lower():
            data["reason"] = reason + " Email not found in passport. User needs to provide email and password during finalization."
        # Ensure email field is explicitly None
        fields["email"] = None

    data["fields"] = fields
    return data
