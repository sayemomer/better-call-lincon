from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date

class DocumentBase(BaseModel):
    filename: str = Field(..., description="Original filename")
    mime_type: str = Field(..., description="MIME type of the document")
    storage_url: str = Field(..., description="URL or path where document is stored")
    type_detected: Optional[str] = Field(None, description="Detected document type (e.g., 'passport', 'study_permit', 'work_permit')")
    date_of_issue: Optional[date] = Field(None, description="Date of issue (extracted from document)")
    date_of_expiry: Optional[date] = Field(None, description="Date of expiry (extracted from document)")

class DocumentCreate(DocumentBase):
    pass

class DocumentOut(DocumentBase):
    id: str
    user_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class RecommendedDocument(BaseModel):
    document_type: str = Field(..., description="Type of document needed")
    description: str = Field(..., description="Description of why this document is needed")
    priority: str = Field(..., description="Priority level: 'high', 'medium', 'low'")
    required_for_crs: bool = Field(False, description="Whether this document is required for CRS score calculation")
    permit_type: Optional[str] = Field(None, description="Relevant permit type: 'study', 'work', or None for both")


class DeadlineItem(BaseModel):
    """Single deadline/expiry entry for dashboard."""

    document_id: str = Field(..., description="Document ID (or signup_job ID for passport from signup)")
    filename: str = Field(..., description="Original filename")
    type_detected: str = Field(..., description="Document type (passport, study_permit, work_permit, etc.)")
    date_of_expiry: Optional[str] = Field(None, description="Expiry date YYYY-MM-DD")
    date_of_issue: Optional[str] = Field(None, description="Issue date YYYY-MM-DD if available")
    days_until_expiry: Optional[int] = Field(
        None,
        description="Days until expiry (negative if already expired)",
    )
    expired: bool = Field(False, description="True if document has already expired")

def _format_date(date_val):
    """Return YYYY-MM-DD only; parse ISO datetime strings."""
    if not date_val:
        return None
    if isinstance(date_val, date) and not isinstance(date_val, datetime):
        return date_val.isoformat()
    if isinstance(date_val, datetime):
        return date_val.date().isoformat()
    if isinstance(date_val, str):
        s = date_val.strip()
        if not s:
            return None
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt.date().isoformat()
        except Exception:
            pass
        try:
            d = datetime.strptime(s[:10], "%Y-%m-%d").date()
            return d.isoformat()
        except Exception:
            return s
    return None


def document_entity(doc: dict) -> dict:
    """Convert MongoDB document to API response format"""
    out = {
        "id": str(doc["_id"]),
        "user_id": str(doc["user_id"]),
        "filename": doc.get("filename"),
        "mime_type": doc.get("mime_type"),
        "storage_url": doc.get("storage_url"),
        "type_detected": doc.get("type_detected"),
        "created_at": doc.get("created_at"),
    }
    out["date_of_issue"] = _format_date(doc.get("date_of_issue"))
    out["date_of_expiry"] = _format_date(doc.get("date_of_expiry"))
    return out
