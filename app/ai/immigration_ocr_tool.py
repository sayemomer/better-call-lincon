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
    """Schema for extracting CRS (Comprehensive Ranking System) profile data from documents.
    
    This schema is designed to extract all fields needed for Express Entry CRS score calculation.
    See: https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/check-score.html
    """
    # Basic info
    dob: Optional[str] = Field(None, description="Date of birth in YYYY-MM-DD format (required for CRS age calculation)")
    citizenship: Optional[str] = Field(None, description="Country of citizenship")
    
    # Marital status & spouse (for CRS spouse factors)
    marital_status: Optional[str] = Field(None, description="Marital status: single, married, common_law, divorced, separated, widowed, annulled")
    spouse_accompanying: Optional[str] = Field(None, description="Will spouse/common-law partner accompany to Canada? true/false")
    spouse_canadian_pr: Optional[str] = Field(None, description="Is spouse/common-law partner a Canadian citizen or PR? true/false")
    
    # Education (for CRS core human capital)
    education_level: Optional[str] = Field(None, description="Highest education level: secondary, one_two_year_diploma, bachelors, masters, phd, two_or_more")
    education_level_detail: Optional[str] = Field(None, description="Education detail: secondary, one- or two-year diploma/certificate, three+ year degree, master's/professional, PhD")
    canadian_education: Optional[str] = Field(None, description="Was this education completed in Canada? true/false (for Canadian study bonus)")
    
    # Language test scores (for CRS first/second official language)
    language_test_type: Optional[str] = Field(None, description="Language test type: ielts, celpip, pte_core, tef_canada, tcf_canada")
    language_speaking: Optional[str] = Field(None, description="Speaking score (IELTS: 0-9, CELPIP: 1-12, PTE: 0-90)")
    language_listening: Optional[str] = Field(None, description="Listening score")
    language_reading: Optional[str] = Field(None, description="Reading score")
    language_writing: Optional[str] = Field(None, description="Writing score")
    second_language_test_type: Optional[str] = Field(None, description="Second official language test type (if applicable)")
    second_language_speaking: Optional[str] = Field(None, description="Second language speaking score")
    second_language_listening: Optional[str] = Field(None, description="Second language listening score")
    second_language_reading: Optional[str] = Field(None, description="Second language reading score")
    second_language_writing: Optional[str] = Field(None, description="Second language writing score")
    
    # Work experience (for CRS core & transferability)
    canadian_work_years: Optional[str] = Field(None, description="Years of skilled work experience in Canada (0-5+, must be TEER 0,1,2,3)")
    foreign_work_years: Optional[str] = Field(None, description="Years of foreign skilled work experience (0-3+, single NOC TEER 0,1,2,3)")
    
    # Additional CRS factors
    certificate_of_qualification: Optional[str] = Field(None, description="Has certificate of qualification from Canadian province/territory? true/false")
    provincial_nomination: Optional[str] = Field(None, description="Has provincial nomination certificate? true/false (adds 600 points)")
    sibling_in_canada: Optional[str] = Field(None, description="Has sibling (18+, citizen/PR) in Canada? true/false")
    
    # Spouse factors (if applicable)
    spouse_education_level: Optional[str] = Field(None, description="Spouse highest education level")
    spouse_canadian_work_years: Optional[str] = Field(None, description="Spouse years of Canadian work experience")
    spouse_language_test_type: Optional[str] = Field(None, description="Spouse language test type")
    spouse_language_speaking: Optional[str] = Field(None, description="Spouse speaking score")
    spouse_language_listening: Optional[str] = Field(None, description="Spouse listening score")
    spouse_language_reading: Optional[str] = Field(None, description="Spouse reading score")
    spouse_language_writing: Optional[str] = Field(None, description="Spouse writing score")
    
    # Legacy fields (for backward compatibility)
    province: Optional[str] = Field(None, description="Province or state")
    city: Optional[str] = Field(None, description="City")
    arrival_date: Optional[str] = Field(None, description="Date of arrival in Canada in YYYY-MM-DD format")
    education: Optional[str] = Field(None, description="[Legacy] Educational qualifications as JSON string")
    language_tests: Optional[str] = Field(None, description="[Legacy] Language test results as JSON string")
    work_experience: Optional[str] = Field(None, description="[Legacy] Work experience details as JSON string")
    document_type: Optional[str] = Field(None, description="Type of document (passport, study_permit, work_permit, degree, language_test, work_reference, etc.)")


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
    
    # Fix anyOf in properties and array types without items - LandingAI doesn't like these
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
            # Fix array types without items - convert to string for JSON parsing
            elif prop_def.get("type") == "array" and "items" not in prop_def:
                cleaned_properties[prop_name] = {"type": "string", "description": prop_def.get("description", "")}
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
    
    # Normalize fields for CRS profile structure
    fields = {}
    
    # Date fields - normalize to YYYY-MM-DD format
    for date_field in ["dob", "arrival_date"]:
        date_val = extracted_data.get(date_field)
        if date_val:
            date_val = str(date_val).strip()
            fields[date_field] = date_val if date_val else None
        else:
            fields[date_field] = None
    
    # Basic string fields
    for str_field in ["citizenship", "province", "city", "document_type", "marital_status",
                      "education_level", "education_level_detail"]:
        val = extracted_data.get(str_field)
        fields[str_field] = (val.strip() if val else None)
    
    # Boolean fields (convert string "true"/"false" to boolean)
    for bool_field in ["spouse_accompanying", "spouse_canadian_pr", "canadian_education",
                       "certificate_of_qualification", "provincial_nomination", "sibling_in_canada"]:
        val = extracted_data.get(bool_field)
        if val is None:
            fields[bool_field] = None
        elif isinstance(val, bool):
            fields[bool_field] = val
        else:
            s = str(val).strip().lower()
            fields[bool_field] = s in ("true", "1", "yes", "y")
    
    # Numeric fields (years, scores)
    for num_field in ["canadian_work_years", "foreign_work_years", "spouse_canadian_work_years",
                      "language_speaking", "language_listening", "language_reading", "language_writing",
                      "second_language_speaking", "second_language_listening", "second_language_reading", "second_language_writing",
                      "spouse_language_speaking", "spouse_language_listening", "spouse_language_reading", "spouse_language_writing"]:
        val = extracted_data.get(num_field)
        if val is None:
            fields[num_field] = None
        else:
            try:
                fields[num_field] = float(val)
            except (TypeError, ValueError):
                fields[num_field] = None
    
    # Test type fields
    for test_field in ["language_test_type", "second_language_test_type", "spouse_language_test_type"]:
        val = extracted_data.get(test_field)
        fields[test_field] = (val.strip().lower() if val else None)
    
    # Spouse education
    val = extracted_data.get("spouse_education_level")
    fields["spouse_education_level"] = (val.strip() if val else None)
    
    # Legacy JSON fields - parse from string to dict (for backward compatibility)
    for json_field in ["education", "language_tests", "work_experience"]:
        val = extracted_data.get(json_field)
        if val:
            if isinstance(val, dict):
                fields[json_field] = val
            elif isinstance(val, str):
                val = val.strip()
                if val:
                    try:
                        fields[json_field] = json.loads(val)
                    except json.JSONDecodeError:
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
