import os
import json
import re
from pathlib import Path
from datetime import datetime, date
from typing import Optional
from landingai_ade import LandingAIADE
from crewai.tools import tool
from pydantic import BaseModel, Field

class SignupDocSchema(BaseModel):
    # Basic identification
    surname: str = Field(description="Surname/Last name of the passport holder")
    given_name: str = Field(description="Given name/First name of the passport holder")
    name: str = Field(description="Full name of the passport holder (surname + given name)")
    dob: str = Field(description="Date of birth in YYYY-MM-DD format")
    citizenship: str = Field(description="Country of citizenship/nationality")
    age: int = Field(description="Age of the person (can be calculated from DOB)")
    sex: str = Field(None, description="Sex/Gender (M, F, or other)")
    place_of_birth: str = Field(None, description="Place of birth (city, country)")
    
    # Passport details
    passport_number: str = Field(description="Passport number")
    country_code: str = Field(None, description="Country code (3-letter ISO code)")
    personal_number: str = Field(None, description="Personal number/National ID number")
    previous_passport_no: str = Field(None, description="Previous passport number if mentioned")
    
    # Dates
    date_of_issue: str = Field(None, description="Date of issue in YYYY-MM-DD format")
    date_of_expiry: str = Field(description="Date of expiry in YYYY-MM-DD format")
    
    # Family information
    fathers_name: str = Field(None, description="Father's name")
    mothers_name: str = Field(None, description="Mother's name")
    marital_status: str = Field(None, description="Marital status (single, married, divorced, widowed, etc.)")
    
    # Address
    permanent_address: str = Field(None, description="Permanent address")
    
    # Travel history (as JSON string - will be parsed after extraction)
    travel_history: Optional[str] = Field(None, description="Travel history as JSON string array (e.g., '[{\"date\": \"2020-01-01\", \"country\": \"USA\", \"purpose\": \"tourism\"}]')")
    
    # Email (usually not in passport)
    email: str = Field(None, description="Email address (usually not in passport)")


def _extract_signup_fields_impl(file_path: str) -> dict:
    """
    Internal implementation of OCR extraction for signup documents.
    This can be called directly without the tool wrapper.
    
    Use ADE to parse and extract structured fields from the uploaded document.
    Returns:
      {
         "fields": {"name": "...", "email": "...", "age": ...},
         "raw": {
            "markdown": "...",
            "extracted": {...}
         }
      }
    """
    api_key = os.getenv("LANDINGAI_API_KEY") or os.getenv("VISION_AGENT_API_KEY")

    if not api_key:
        raise RuntimeError("LANDINGAI_API_KEY or VISION_AGENT_API_KEY not set")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Initialize LandingAI client
    ade = LandingAIADE(apikey=api_key)
    
    # Step 1: Parse document to get markdown
    with open(file_path, "rb") as f:
        parse_result = ade.parse(document=f)
    
    # Extract markdown from parse result
    markdown_content = parse_result.markdown if parse_result.markdown else ""
    
    if not markdown_content:
        raise RuntimeError("No markdown extracted from document")
    
    # Step 2: Create JSON schema from Pydantic model
    schema_dict = SignupDocSchema.model_json_schema()
    
    # Clean up schema to ensure LandingAI compatibility
    # Remove definitions that might cause issues
    if "definitions" in schema_dict:
        del schema_dict["definitions"]
    
    # Fix anyOf in properties and array types without items
    if "properties" in schema_dict:
        cleaned_properties = {}
        for prop_name, prop_def in schema_dict["properties"].items():
            # If anyOf exists, extract the non-null type
            if "anyOf" in prop_def:
                any_of_list = prop_def["anyOf"]
                # Find the first non-null type
                found_type = None
                for option in any_of_list:
                    if isinstance(option, dict) and option.get("type") != "null":
                        found_type = option
                        break
                # Use the found type, or keep original if none found
                if found_type:
                    cleaned_properties[prop_name] = found_type
                else:
                    cleaned_properties[prop_name] = prop_def
            # Fix array types without items
            elif prop_def.get("type") == "array" and "items" not in prop_def:
                # Remove array type - convert to string for JSON parsing
                cleaned_properties[prop_name] = {"type": "string", "description": prop_def.get("description", "")}
            else:
                cleaned_properties[prop_name] = prop_def
        schema_dict["properties"] = cleaned_properties
    
    # Step 3: Extract structured data using the schema
    extract_resp = ade.extract(
        schema=json.dumps(schema_dict),
        markdown=markdown_content,
    )
    
    # Parse extracted data - ExtractResponse has 'extraction' field
    extracted_data = {}
    if hasattr(extract_resp, 'extraction'):
        extracted_data = extract_resp.extraction
        if isinstance(extracted_data, str):
            extracted_data = json.loads(extracted_data)
    elif hasattr(extract_resp, 'data'):
        extracted_data = extract_resp.data
        if isinstance(extracted_data, str):
            extracted_data = json.loads(extracted_data)
    elif isinstance(extract_resp, dict):
        extracted_data = extract_resp
    
    def parse_date(date_str):
        """Parse date string in various formats to YYYY-MM-DD"""
        if not date_str:
            return None
        date_str = str(date_str).strip()
        date_formats = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y", "%Y.%m.%d"]
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt).date()
                return parsed_date.isoformat()
            except (ValueError, TypeError):
                continue
        return None
    
    # Normalize and validate basic fields
    surname = (extracted_data.get("surname") or "").strip() or None
    given_name = (extracted_data.get("given_name") or "").strip() or None
    name = (extracted_data.get("name") or "").strip() or None
    # If name not provided but surname/given_name are, construct name
    if not name and surname and given_name:
        name = f"{given_name} {surname}".strip()
    elif not name and surname:
        name = surname
    elif not name and given_name:
        name = given_name
    
    dob_str = (extracted_data.get("dob") or "").strip() or None
    dob_iso = parse_date(dob_str)
    
    citizenship = (extracted_data.get("citizenship") or "").strip() or None
    sex = (extracted_data.get("sex") or "").strip().upper() or None
    if sex and sex not in ["M", "F", "MALE", "FEMALE"]:
        sex = None
    
    place_of_birth = (extracted_data.get("place_of_birth") or "").strip() or None
    
    # Passport details
    passport_number = (extracted_data.get("passport_number") or "").strip() or None
    country_code = (extracted_data.get("country_code") or "").strip().upper() or None
    personal_number = (extracted_data.get("personal_number") or "").strip() or None
    previous_passport_no = (extracted_data.get("previous_passport_no") or "").strip() or None
    
    # Dates
    date_of_issue_str = (extracted_data.get("date_of_issue") or "").strip() or None
    date_of_issue_iso = parse_date(date_of_issue_str)
    
    date_of_expiry_str = (extracted_data.get("date_of_expiry") or "").strip() or None
    date_of_expiry_iso = parse_date(date_of_expiry_str)
    
    # Family information
    fathers_name = (extracted_data.get("fathers_name") or "").strip() or None
    mothers_name = (extracted_data.get("mothers_name") or "").strip() or None
    marital_status = (extracted_data.get("marital_status") or "").strip().lower() or None
    
    # Address
    permanent_address = (extracted_data.get("permanent_address") or "").strip() or None
    
    # Travel history
    travel_history = extracted_data.get("travel_history")
    if travel_history and isinstance(travel_history, str):
        try:
            travel_history = json.loads(travel_history)
        except:
            travel_history = None
    if not isinstance(travel_history, list):
        travel_history = None
    
    # Email (usually not in passport)
    email = (extracted_data.get("email") or "").strip().lower() or None
    if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        email = None
    
    # Age
    age = extracted_data.get("age")
    if age is not None:
        try:
            age = int(age)
            if age < 0 or age > 120:
                age = None
        except (ValueError, TypeError):
            age = None
    
    # Calculate age from DOB if age not provided but DOB is available
    if age is None and dob_iso:
        try:
            dob_date = datetime.strptime(dob_iso, "%Y-%m-%d").date()
            today = date.today()
            age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
            if age < 0 or age > 120:
                age = None
        except Exception:
            age = None

    return {
        "fields": {
            "surname": surname,
            "given_name": given_name,
            "name": name,
            "dob": dob_iso,
            "citizenship": citizenship,
            "sex": sex,
            "place_of_birth": place_of_birth,
            "passport_number": passport_number,
            "country_code": country_code,
            "personal_number": personal_number,
            "previous_passport_no": previous_passport_no,
            "date_of_issue": date_of_issue_iso,
            "date_of_expiry": date_of_expiry_iso,
            "fathers_name": fathers_name,
            "mothers_name": mothers_name,
            "marital_status": marital_status,
            "permanent_address": permanent_address,
            "travel_history": travel_history,
            "email": email,
            "age": age
        },
        "raw": {
            "markdown": markdown_content if markdown_content else None,
            "extracted": extracted_data
        }
    }

@tool("landingai_ocr_extract_signup_doc_fields")
def landingai_ocr_extract_signup_fields(file_path: str) -> dict:
    """
    CrewAI tool wrapper for OCR extraction.
    Use _extract_signup_fields_impl for direct calls.
    """
    return _extract_signup_fields_impl(file_path)
