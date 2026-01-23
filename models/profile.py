from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import date, datetime

class ProfileBase(BaseModel):
    status: Optional[str] = Field(None, description="Profile status (e.g., 'active', 'pending', 'incomplete')")
    dob: Optional[date] = Field(None, description="Date of birth")
    citizenship: Optional[str] = Field(None, description="Country of citizenship")
    province: Optional[str] = Field(None, description="Province/State")
    city: Optional[str] = Field(None, description="City")
    arrival_date: Optional[date] = Field(None, description="Date of arrival in Canada")
    education_json: Optional[Dict[str, Any]] = Field(None, description="Educational history in JSON format")
    language_json: Optional[Dict[str, Any]] = Field(None, description="Language proficiency in JSON format")
    work_json: Optional[Dict[str, Any]] = Field(None, description="Work experience in JSON format")

class ProfileCreate(ProfileBase):
    pass

class ProfileUpdate(BaseModel):
    status: Optional[str] = None
    dob: Optional[date] = None
    citizenship: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    arrival_date: Optional[date] = None
    education_json: Optional[Dict[str, Any]] = None
    language_json: Optional[Dict[str, Any]] = None
    work_json: Optional[Dict[str, Any]] = None

class ProfileOut(ProfileBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ProfileValidationResult(BaseModel):
    is_valid: bool
    missing_fields: list[str]
    incomplete_sections: list[str]
    recommendations: list[str]

def profile_entity(profile: dict) -> dict:
    """Convert MongoDB profile document to API response format"""
    def format_date(date_val):
        """Format date value to ISO string"""
        if not date_val:
            return None
        if isinstance(date_val, date):
            return date_val.isoformat()
        if isinstance(date_val, datetime):
            return date_val.date().isoformat()
        if isinstance(date_val, str):
            return date_val
        return None
    
    return {
        "id": str(profile["_id"]),
        "user_id": str(profile.get("user_id", profile["_id"])),
        "status": profile.get("status"),
        "dob": format_date(profile.get("dob")),
        "citizenship": profile.get("citizenship"),
        "province": profile.get("province"),
        "city": profile.get("city"),
        "arrival_date": format_date(profile.get("arrival_date")),
        "education_json": profile.get("education_json"),
        "language_json": profile.get("language_json"),
        "work_json": profile.get("work_json"),
        "created_at": profile.get("created_at"),
        "updated_at": profile.get("updated_at"),
    }
