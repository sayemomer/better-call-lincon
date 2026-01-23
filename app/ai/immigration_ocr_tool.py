import os
import json
import re
from pathlib import Path
from landingai_ade import LandingAIADE
from crewai.tools import tool
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import date

class ImmigrationProfileSchema(BaseModel):
    """Schema for extracting immigration profile data from documents"""
    dob: Optional[str] = Field(None, description="Date of birth in YYYY-MM-DD format")
    citizenship: Optional[str] = Field(None, description="Country of citizenship")
    province: Optional[str] = Field(None, description="Province or state")
    city: Optional[str] = Field(None, description="City")
    arrival_date: Optional[str] = Field(None, description="Date of arrival in Canada in YYYY-MM-DD format")
    education: Optional[str] = Field(None, description="Educational qualifications as JSON string (e.g., '{\"degree\": \"Bachelor\", \"university\": \"...\", \"year\": 2020}')")
    language_tests: Optional[str] = Field(None, description="Language test results as JSON string (e.g., '{\"ielts\": {\"reading\": 7, \"writing\": 7, \"listening\": 8, \"speaking\": 7}}')")
    work_experience: Optional[str] = Field(None, description="Work experience details as JSON string (e.g., '{\"years\": 5, \"positions\": [...]}')")
    document_type: Optional[str] = Field(None, description="Type of document (passport, study_permit, work_permit, degree, language_test, etc.)")


@tool("landingai_ocr_extract_immigration_fields")
def landingai_ocr_extract_immigration_fields(file_path: str) -> dict:
    """
    Use ADE to parse and extract structured immigration profile fields from uploaded documents.
    Returns:
      {
         "fields": {
            "dob": "...",
            "citizenship": "...",
            "province": "...",
            "city": "...",
            "arrival_date": "...",
            "education": {...},
            "language_tests": {...},
            "work_experience": {...},
            "document_type": "..."
         },
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
    schema_dict = ImmigrationProfileSchema.model_json_schema()
    
    # Clean up schema to ensure LandingAI compatibility
    # Remove definitions that might cause issues
    if "definitions" in schema_dict:
        del schema_dict["definitions"]
    
    # Fix anyOf in properties - LandingAI doesn't like anyOf without properties
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
            else:
                cleaned_properties[prop_name] = prop_def
        schema_dict["properties"] = cleaned_properties
    
    # Step 3: Extract structured data using the schema
    extract_resp = ade.extract(
        schema=json.dumps(schema_dict),
        markdown=markdown_content,
    )
    
    # Parse extracted data
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
    
    # Normalize fields
    fields = {}
    
    # Date fields - normalize to YYYY-MM-DD format
    for date_field in ["dob", "arrival_date"]:
        date_val = extracted_data.get(date_field)
        if date_val:
            # Try to normalize date format
            date_val = str(date_val).strip()
            fields[date_field] = date_val if date_val else None
        else:
            fields[date_field] = None
    
    # String fields
    for str_field in ["citizenship", "province", "city", "document_type"]:
        val = extracted_data.get(str_field)
        fields[str_field] = (val.strip() if val else None)
    
    # JSON fields - parse from string to dict
    for json_field in ["education", "language_tests", "work_experience"]:
        val = extracted_data.get(json_field)
        if val:
            # If it's already a dict, use it
            if isinstance(val, dict):
                fields[json_field] = val
            # If it's a string, try to parse as JSON
            elif isinstance(val, str):
                val = val.strip()
                if val:
                    try:
                        fields[json_field] = json.loads(val)
                    except json.JSONDecodeError:
                        # If not valid JSON, try to create a simple structure
                        fields[json_field] = {"raw": val}
                else:
                    fields[json_field] = None
            else:
                fields[json_field] = None
        else:
            fields[json_field] = None

    return {
        "fields": fields,
        "raw": {
            "markdown": markdown_content[:500] if markdown_content else None,
            "extracted": extracted_data
        }
    }
