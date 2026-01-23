"""
Utility module for recommending immigration documents based on permit type and CRS score requirements.
"""

from typing import List, Dict, Any, Optional
from models.document import RecommendedDocument

# Document requirements for CRS score calculation
CRS_REQUIRED_DOCUMENTS = [
    {
        "document_type": "passport",
        "description": "Valid passport for identity verification and citizenship confirmation",
        "priority": "high",
        "required_for_crs": True,
        "permit_type": None,  # Required for both
    },
    {
        "document_type": "language_test",
        "description": "Language test results (IELTS, CELPIP, TEF) for language proficiency points",
        "priority": "high",
        "required_for_crs": True,
        "permit_type": None,
    },
    {
        "document_type": "education_credential",
        "description": "Educational credentials (degrees, diplomas) for education points",
        "priority": "high",
        "required_for_crs": True,
        "permit_type": None,
    },
    {
        "document_type": "work_reference",
        "description": "Work reference letters and experience documents for work experience points",
        "priority": "high",
        "required_for_crs": True,
        "permit_type": None,
    },
]

# Additional documents for study permit holders
STUDY_PERMIT_DOCUMENTS = [
    {
        "document_type": "study_permit",
        "description": "Current study permit for status verification",
        "priority": "high",
        "required_for_crs": False,
        "permit_type": "study",
    },
    {
        "document_type": "transcript",
        "description": "Academic transcripts for education assessment",
        "priority": "medium",
        "required_for_crs": True,
        "permit_type": "study",
    },
    {
        "document_type": "enrollment_letter",
        "description": "Letter of enrollment from educational institution",
        "priority": "medium",
        "required_for_crs": False,
        "permit_type": "study",
    },
]

# Additional documents for work permit holders
WORK_PERMIT_DOCUMENTS = [
    {
        "document_type": "work_permit",
        "description": "Current work permit for status verification",
        "priority": "high",
        "required_for_crs": False,
        "permit_type": "work",
    },
    {
        "document_type": "employment_letter",
        "description": "Current employment letter for work experience validation",
        "priority": "high",
        "required_for_crs": True,
        "permit_type": "work",
    },
    {
        "document_type": "pay_stubs",
        "description": "Recent pay stubs for employment verification",
        "priority": "medium",
        "required_for_crs": False,
        "permit_type": "work",
    },
    {
        "document_type": "tax_documents",
        "description": "Tax documents (T4, NOA) for income verification",
        "priority": "medium",
        "required_for_crs": False,
        "permit_type": "work",
    },
]

def get_recommended_documents(
    permit_type: Optional[str] = None,
    uploaded_document_types: List[str] = None
) -> List[RecommendedDocument]:
    """
    Get recommended documents based on permit type and already uploaded documents.
    
    Args:
        permit_type: "study", "work", or None for both
        uploaded_document_types: List of document types already uploaded
    
    Returns:
        List of recommended documents
    """
    if uploaded_document_types is None:
        uploaded_document_types = []
    
    recommended = []
    
    # Always include CRS-required documents
    for doc in CRS_REQUIRED_DOCUMENTS:
        if doc["document_type"] not in uploaded_document_types:
            recommended.append(RecommendedDocument(**doc))
    
    # Add permit-specific documents
    if permit_type == "study":
        for doc in STUDY_PERMIT_DOCUMENTS:
            if doc["document_type"] not in uploaded_document_types:
                recommended.append(RecommendedDocument(**doc))
    elif permit_type == "work":
        for doc in WORK_PERMIT_DOCUMENTS:
            if doc["document_type"] not in uploaded_document_types:
                recommended.append(RecommendedDocument(**doc))
    else:
        # If permit type is unknown, include both study and work permit documents
        for doc in STUDY_PERMIT_DOCUMENTS + WORK_PERMIT_DOCUMENTS:
            if doc["document_type"] not in uploaded_document_types:
                recommended.append(RecommendedDocument(**doc))
    
    # Sort by priority (high first) and then by required_for_crs
    recommended.sort(key=lambda x: (
        x.priority != "high",  # High priority first
        not x.required_for_crs  # CRS-required first
    ))
    
    return recommended

def detect_permit_type_from_documents(document_types: List[str]) -> Optional[str]:
    """
    Detect permit type from uploaded document types.
    
    Args:
        document_types: List of document type strings
    
    Returns:
        "study", "work", or None
    """
    if not document_types:
        return None
    
    document_types_lower = [dt.lower() for dt in document_types]
    
    if any("study" in dt for dt in document_types_lower):
        return "study"
    elif any("work" in dt for dt in document_types_lower):
        return "work"
    
    return None
