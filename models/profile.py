from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import date, datetime

class ProfileBase(BaseModel):
    status: Optional[str] = Field(None, description="Profile status (e.g., 'active', 'pending', 'incomplete')")
    
    # Basic identification
    surname: Optional[str] = Field(None, description="Surname/Last name")
    given_name: Optional[str] = Field(None, description="Given name/First name")
    dob: Optional[date] = Field(None, description="Date of birth")
    citizenship: Optional[str] = Field(None, description="Country of citizenship")
    sex: Optional[str] = Field(None, description="Sex/Gender")
    place_of_birth: Optional[str] = Field(None, description="Place of birth")
    
    # Passport details
    passport_number: Optional[str] = Field(None, description="Passport number")
    country_code: Optional[str] = Field(None, description="Country code (3-letter ISO)")
    personal_number: Optional[str] = Field(None, description="Personal number/National ID")
    previous_passport_no: Optional[str] = Field(None, description="Previous passport number")
    date_of_issue: Optional[date] = Field(None, description="Passport date of issue")
    date_of_expiry: Optional[date] = Field(None, description="Passport date of expiry")
    
    # Family information
    fathers_name: Optional[str] = Field(None, description="Father's name")
    mothers_name: Optional[str] = Field(None, description="Mother's name")
    marital_status: Optional[str] = Field(None, description="Marital status")
    
    # Address
    permanent_address: Optional[str] = Field(None, description="Permanent address")
    
    # Travel history
    travel_history: Optional[list] = Field(None, description="Travel history as JSON array")
    
    # Location in Canada
    province: Optional[str] = Field(None, description="Province/State")
    city: Optional[str] = Field(None, description="City")
    arrival_date: Optional[date] = Field(None, description="Date of arrival in Canada")
    
    # Additional documents
    education_json: Optional[Dict[str, Any]] = Field(None, description="Educational history in JSON format")
    language_json: Optional[Dict[str, Any]] = Field(None, description="Language proficiency in JSON format")
    work_json: Optional[Dict[str, Any]] = Field(None, description="Work experience in JSON format")

class ProfileCreate(ProfileBase):
    pass

class ProfileUpdate(BaseModel):
    status: Optional[str] = None
    surname: Optional[str] = None
    given_name: Optional[str] = None
    dob: Optional[date] = None
    citizenship: Optional[str] = None
    sex: Optional[str] = None
    place_of_birth: Optional[str] = None
    passport_number: Optional[str] = None
    country_code: Optional[str] = None
    personal_number: Optional[str] = None
    previous_passport_no: Optional[str] = None
    date_of_issue: Optional[date] = None
    date_of_expiry: Optional[date] = None
    fathers_name: Optional[str] = None
    mothers_name: Optional[str] = None
    marital_status: Optional[str] = None
    permanent_address: Optional[str] = None
    travel_history: Optional[list] = None
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
        # Basic identification
        "surname": profile.get("surname"),
        "given_name": profile.get("given_name"),
        "dob": format_date(profile.get("dob")),
        "citizenship": profile.get("citizenship"),
        "sex": profile.get("sex"),
        "place_of_birth": profile.get("place_of_birth"),
        # Passport details
        "passport_number": profile.get("passport_number"),
        "country_code": profile.get("country_code"),
        "personal_number": profile.get("personal_number"),
        "previous_passport_no": profile.get("previous_passport_no"),
        "date_of_issue": format_date(profile.get("date_of_issue")),
        "date_of_expiry": format_date(profile.get("date_of_expiry")),
        # Family information
        "fathers_name": profile.get("fathers_name"),
        "mothers_name": profile.get("mothers_name"),
        "marital_status": profile.get("marital_status"),
        # Address
        "permanent_address": profile.get("permanent_address"),
        # Travel history
        "travel_history": profile.get("travel_history"),
        # Location in Canada
        "province": profile.get("province"),
        "city": profile.get("city"),
        "arrival_date": format_date(profile.get("arrival_date")),
        # Additional documents
        "education_json": profile.get("education_json"),
        "language_json": profile.get("language_json"),
        "work_json": profile.get("work_json"),
        "created_at": profile.get("created_at"),
        "updated_at": profile.get("updated_at"),
    }
