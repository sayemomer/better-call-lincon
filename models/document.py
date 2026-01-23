from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class DocumentBase(BaseModel):
    filename: str = Field(..., description="Original filename")
    mime_type: str = Field(..., description="MIME type of the document")
    storage_url: str = Field(..., description="URL or path where document is stored")
    type_detected: Optional[str] = Field(None, description="Detected document type (e.g., 'passport', 'study_permit', 'work_permit')")

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

def document_entity(doc: dict) -> dict:
    """Convert MongoDB document to API response format"""
    return {
        "id": str(doc["_id"]),
        "user_id": str(doc["user_id"]),
        "filename": doc.get("filename"),
        "mime_type": doc.get("mime_type"),
        "storage_url": doc.get("storage_url"),
        "type_detected": doc.get("type_detected"),
        "created_at": doc.get("created_at"),
    }
