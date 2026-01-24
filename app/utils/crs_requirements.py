"""
Utility to determine CRS calculation requirements and document needs.
"""

from typing import Dict, List, Any, Optional
from datetime import date, datetime


class CRSFieldRequirement:
    """Represents a field requirement for CRS calculation"""
    def __init__(
        self,
        field_name: str,
        field_type: str,  # "required", "optional", "conditional"
        description: str,
        source_documents: List[str],  # Types of documents that provide this field
        current_value: Any = None,
        is_present: bool = False,
    ):
        self.field_name = field_name
        self.field_type = field_type
        self.description = description
        self.source_documents = source_documents
        self.current_value = current_value
        self.is_present = is_present


def analyze_crs_requirements(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze profile data to determine what's available and what's needed for CRS calculation.
    
    Returns a dictionary with:
    - available_fields: fields that are present
    - missing_required: required fields that are missing
    - missing_optional: optional fields that could improve score
    - can_calculate: whether minimum requirements are met
    - requirements: detailed list of all field requirements
    """
    requirements = []
    available_fields = []
    missing_required = []
    missing_optional = []
    
    # Calculate age from DOB if not provided
    age_value = profile_data.get("age")
    dob_value = profile_data.get("dob")
    has_age_or_dob = bool(age_value or dob_value)
    
    # If we have DOB but not age, calculate it
    if not age_value and dob_value:
        try:
            from datetime import datetime, date
            dob_date = None
            if isinstance(dob_value, str):
                try:
                    dob_date = datetime.fromisoformat(dob_value.replace("Z", "+00:00")).date()
                except:
                    try:
                        dob_date = datetime.strptime(dob_value, "%Y-%m-%d").date()
                    except:
                        pass
            elif isinstance(dob_value, datetime):
                dob_date = dob_value.date()
            elif isinstance(dob_value, date):
                dob_date = dob_value
            
            if dob_date:
                today = date.today()
                age_calculated = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
                if age_calculated > 0 and age_calculated < 120:
                    age_value = age_calculated
                    profile_data["age"] = age_value  # Update profile_data for consistency
        except Exception:
            pass
    
    # Required fields for basic CRS calculation
    required_fields = [
        CRSFieldRequirement(
            "age",
            "required",
            "Age (or DOB to calculate age) - needed for age points",
            ["passport"],
            age_value or (dob_value and "can calculate from DOB"),
            bool(age_value or dob_value),
        ),
        CRSFieldRequirement(
            "education_level",
            "required",
            "Education level - needed for education points",
            ["degree", "diploma", "transcript", "education_credential"],
            profile_data.get("education_level") or profile_data.get("education_level_detail"),
            bool(profile_data.get("education_level") or profile_data.get("education_level_detail")),
        ),
        CRSFieldRequirement(
            "language_scores",
            "required",
            "Language test scores (test type + at least one skill) - needed for language points",
            ["language_test", "ielts", "celpip", "pte", "tef"],
            profile_data.get("language_scores"),
            bool(profile_data.get("language_scores") and isinstance(profile_data.get("language_scores"), dict)),
        ),
    ]
    
    # Optional but important fields
    optional_fields = [
        CRSFieldRequirement(
            "marital_status",
            "optional",
            "Marital status - affects scoring if spouse is accompanying",
            ["passport", "marriage_certificate"],
            profile_data.get("marital_status"),
            bool(profile_data.get("marital_status")),
        ),
        CRSFieldRequirement(
            "canadian_work_years",
            "optional",
            "Canadian work experience years - adds significant points",
            ["work_permit", "employment_letter", "pay_stubs", "work_reference"],
            profile_data.get("canadian_work_years"),
            bool(profile_data.get("canadian_work_years")),
        ),
        CRSFieldRequirement(
            "foreign_work_years",
            "optional",
            "Foreign work experience years - adds points via transferability",
            ["work_reference", "employment_letter"],
            profile_data.get("foreign_work_years"),
            bool(profile_data.get("foreign_work_years")),
        ),
        CRSFieldRequirement(
            "canadian_education",
            "optional",
            "Canadian education indicator - adds bonus points",
            ["transcript", "degree", "diploma"],
            profile_data.get("canadian_education"),
            bool(profile_data.get("canadian_education")),
        ),
        CRSFieldRequirement(
            "second_language_scores",
            "optional",
            "Second official language test scores - adds bonus points",
            ["language_test", "ielts", "celpip", "pte", "tef"],
            profile_data.get("second_language_scores"),
            bool(profile_data.get("second_language_scores")),
        ),
        CRSFieldRequirement(
            "provincial_nomination",
            "optional",
            "Provincial nomination certificate - adds 600 points",
            ["provincial_nomination"],
            profile_data.get("provincial_nomination"),
            bool(profile_data.get("provincial_nomination")),
        ),
        CRSFieldRequirement(
            "certificate_of_qualification",
            "optional",
            "Certificate of qualification - adds points",
            ["certificate_of_qualification"],
            profile_data.get("certificate_of_qualification"),
            bool(profile_data.get("certificate_of_qualification")),
        ),
        CRSFieldRequirement(
            "sibling_in_canada",
            "optional",
            "Sibling in Canada - adds points",
            ["sibling_documents"],
            profile_data.get("sibling_in_canada"),
            bool(profile_data.get("sibling_in_canada")),
        ),
    ]
    
    # Check language scores in detail
    lang_scores = profile_data.get("language_scores") or {}
    if isinstance(lang_scores, dict):
        has_test_type = bool(lang_scores.get("test"))
        has_skills = any(
            lang_scores.get(skill) is not None
            for skill in ["speaking", "listening", "reading", "writing"]
        )
        if not has_test_type or not has_skills:
            # Language scores are incomplete
            for req in required_fields:
                if req.field_name == "language_scores":
                    req.is_present = False
                    req.current_value = None
    
    # Categorize fields
    for req in required_fields:
        requirements.append({
            "field_name": req.field_name,
            "field_type": req.field_type,
            "description": req.description,
            "source_documents": req.source_documents,
            "is_present": req.is_present,
            "current_value": req.current_value,
        })
        if req.is_present:
            available_fields.append(req.field_name)
        else:
            missing_required.append(req.field_name)
    
    for req in optional_fields:
        requirements.append({
            "field_name": req.field_name,
            "field_type": req.field_type,
            "description": req.description,
            "source_documents": req.source_documents,
            "is_present": req.is_present,
            "current_value": req.current_value,
        })
        if req.is_present:
            available_fields.append(req.field_name)
        else:
            missing_optional.append(req.field_name)
    
    # Check if we can calculate CRS meaningfully
    # Need at least 3 documents/fields: passport (age), education, and language test
    # Only return can_calculate=true if ALL required fields are present
    can_calculate = len(missing_required) == 0  # True only if all required fields are present
    is_complete = len(missing_required) == 0 and len(missing_optional) == 0  # True if all fields (required + optional) are present
    
    return {
        "can_calculate": can_calculate,
        "is_complete": is_complete,  # Whether all fields (required + optional) are present
        "available_fields": available_fields,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "requirements": requirements,
    }


def get_required_documents_for_crs(
    profile_data: Dict[str, Any],
    uploaded_document_types: List[str]
) -> List[Dict[str, Any]]:
    """
    Determine which documents are needed based on missing CRS fields.
    
    Args:
        profile_data: Current profile data
        uploaded_document_types: List of document types already uploaded
    
    Returns:
        List of required documents with priority and description
    """
    analysis = analyze_crs_requirements(profile_data)
    required_docs = []
    
    # Passport is always required (users sign up with passport, but check if uploaded)
    # Normalize document types for comparison (case-insensitive)
    normalized_uploaded = [dt.lower() if dt else "" for dt in uploaded_document_types]
    has_passport = any("passport" in dt for dt in normalized_uploaded)
    
    if not has_passport:
        required_docs.append({
            "document_type": "passport",
            "priority": "high",
            "required_for_crs": True,
            "reason": "Required for age/DOB and identity verification (used during signup)",
            "field_needed": "age",
        })
    
    # Map missing fields to document types
    field_to_docs = {
        "age": ["passport"],  # Already handled above, but keep for reference
        "education_level": ["degree", "diploma", "transcript", "education_credential"],
        "language_scores": ["language_test", "ielts", "celpip", "pte_core", "tef_canada", "tcf_canada"],
        "canadian_work_years": ["work_permit", "employment_letter", "pay_stubs", "work_reference"],
        "foreign_work_years": ["work_reference", "employment_letter"],
        "canadian_education": ["transcript", "degree", "diploma"],
        "second_language_scores": ["language_test", "ielts", "celpip", "pte_core", "tef_canada", "tcf_canada"],
        "provincial_nomination": ["provincial_nomination"],
        "certificate_of_qualification": ["certificate_of_qualification"],
    }
    
    # Check each missing required field
    for field in analysis["missing_required"]:
        doc_types = field_to_docs.get(field, [])
        for doc_type in doc_types:
            # Normalize for comparison (case-insensitive, handle variations)
            doc_type_lower = doc_type.lower()
            if not any(doc_type_lower in dt.lower() or dt.lower() in doc_type_lower for dt in uploaded_document_types):
                required_docs.append({
                    "document_type": doc_type,
                    "priority": "high",
                    "required_for_crs": True,
                    "reason": f"Required for {field} field",
                    "field_needed": field,
                })
    
    # Check optional fields (lower priority)
    for field in analysis["missing_optional"]:
        doc_types = field_to_docs.get(field, [])
        for doc_type in doc_types:
            # Normalize for comparison
            doc_type_lower = doc_type.lower()
            if not any(doc_type_lower in dt.lower() or dt.lower() in doc_type_lower for dt in uploaded_document_types):
                # Check if this doc type is already in required_docs
                if not any(d["document_type"].lower() == doc_type_lower for d in required_docs):
                    required_docs.append({
                        "document_type": doc_type,
                        "priority": "medium",
                        "required_for_crs": False,
                        "reason": f"Optional but improves score for {field}",
                        "field_needed": field,
                    })
    
    # Remove duplicates and sort by priority
    seen = set()
    unique_docs = []
    for doc in required_docs:
        key = doc["document_type"]
        if key not in seen:
            seen.add(key)
            unique_docs.append(doc)
    
    # Sort: high priority first, then by required_for_crs
    unique_docs.sort(key=lambda x: (x["priority"] != "high", not x["required_for_crs"]))
    
    return unique_docs
