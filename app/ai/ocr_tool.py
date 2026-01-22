import os
import json
import re
from pathlib import Path
from landingai_ade import LandingAIADE
from crewai.tools import tool
from pydantic import BaseModel, Field

class SignupDocSchema(BaseModel):
    name: str = Field(description="Person's name")
    email: str = Field(description="Email address")
    age: int = Field(description="Age of the person")


@tool("landingai_ocr_extract_signup_doc_fields")
def landingai_ocr_extract_signup_fields(file_path: str) -> dict:
    """
    Use ADE to parse and extract structured fields from the uploaded document.
    Returns:
      {
         "fields": {"name": "...", "email": "...", "age": ...},
         "confidence": {"name": ..., "email": ..., "age": ..., "overall": ...},
         "raw_parse": {...}  # raw parse output (optional)
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
    
    # Normalize and validate fields
    name = (extracted_data.get("name") or "").strip() or None
    email = (extracted_data.get("email") or "").strip().lower() or None
    age = extracted_data.get("age")
    
    # Validate email format
    if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        email = None
    
    # Validate and convert age
    if age is not None:
        try:
            age = int(age)
            if age < 0 or age > 120:
                age = None
        except (ValueError, TypeError):
            age = None

    return {
        "fields": {
            "name": name,
            "email": email,
            "age": age
        },
        "raw": {
            "markdown": markdown_content[:500] if markdown_content else None,
            "extracted": extracted_data
        }
    }
