from fastapi import APIRouter, HTTPException, Request, Depends
from bson import ObjectId
from datetime import datetime, timezone, date
from typing import Optional
from app.db import get_db
from app.auth.deps import get_current_user
from models.profile import ProfileCreate, ProfileUpdate, ProfileOut, ProfileValidationResult, profile_entity

router = APIRouter(tags=["profile"])

@router.get("/profile", response_model=ProfileOut)
async def get_profile(request: Request, user: dict = Depends(get_current_user)):
    """Get the current user's immigration profile"""
    db = get_db(request)
    user_id = ObjectId(user["id"])
    
    profile = await db.profiles.find_one({"user_id": user_id})
    
    if not profile:
        # Create empty profile if it doesn't exist
        now = datetime.now(timezone.utc)
        profile_data = {
            "user_id": user_id,
            "status": "incomplete",
            "created_at": now,
            "updated_at": now,
        }
        result = await db.profiles.insert_one(profile_data)
        profile = await db.profiles.find_one({"_id": result.inserted_id})
    
    return profile_entity(profile)

@router.put("/profile", response_model=ProfileOut)
async def update_profile_full(
    profile: ProfileCreate,
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Update the entire profile (PUT - replaces existing profile)"""
    db = get_db(request)
    user_id = ObjectId(user["id"])
    
    # Convert date strings to date objects if needed
    profile_dict = profile.dict(exclude_none=True)
    
    # Handle date fields
    if "dob" in profile_dict and isinstance(profile_dict["dob"], str):
        profile_dict["dob"] = datetime.fromisoformat(profile_dict["dob"]).date()
    if "arrival_date" in profile_dict and isinstance(profile_dict["arrival_date"], str):
        profile_dict["arrival_date"] = datetime.fromisoformat(profile_dict["arrival_date"]).date()
    
    profile_dict["user_id"] = user_id
    profile_dict["updated_at"] = datetime.now(timezone.utc)
    
    # Check if profile exists
    existing = await db.profiles.find_one({"user_id": user_id})
    
    if existing:
        # Update existing profile
        await db.profiles.update_one(
            {"user_id": user_id},
            {"$set": profile_dict}
        )
        updated_profile = await db.profiles.find_one({"user_id": user_id})
    else:
        # Create new profile
        profile_dict["created_at"] = datetime.now(timezone.utc)
        result = await db.profiles.insert_one(profile_dict)
        updated_profile = await db.profiles.find_one({"_id": result.inserted_id})
    
    return profile_entity(updated_profile)

@router.patch("/profile", response_model=ProfileOut)
async def update_profile_partial(
    profile: ProfileUpdate,
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Partially update the profile (PATCH - updates only provided fields)"""
    db = get_db(request)
    user_id = ObjectId(user["id"])
    
    # Get only non-None fields
    update_data = profile.dict(exclude_none=True)
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    # Handle date fields
    if "dob" in update_data and isinstance(update_data["dob"], str):
        update_data["dob"] = datetime.fromisoformat(update_data["dob"]).date()
    if "arrival_date" in update_data and isinstance(update_data["arrival_date"], str):
        update_data["arrival_date"] = datetime.fromisoformat(update_data["arrival_date"]).date()
    
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    # Check if profile exists
    existing = await db.profiles.find_one({"user_id": user_id})
    
    if not existing:
        # Create new profile with provided fields
        update_data["user_id"] = user_id
        update_data["status"] = update_data.get("status", "incomplete")
        update_data["created_at"] = datetime.now(timezone.utc)
        result = await db.profiles.insert_one(update_data)
        updated_profile = await db.profiles.find_one({"_id": result.inserted_id})
    else:
        # Update existing profile
        await db.profiles.update_one(
            {"user_id": user_id},
            {"$set": update_data}
        )
        updated_profile = await db.profiles.find_one({"user_id": user_id})
    
    return profile_entity(updated_profile)

@router.get("/profile/validate", response_model=ProfileValidationResult)
async def validate_profile(request: Request, user: dict = Depends(get_current_user)):
    """Validate the profile completeness and provide recommendations"""
    db = get_db(request)
    user_id = ObjectId(user["id"])
    
    profile = await db.profiles.find_one({"user_id": user_id})
    
    if not profile:
        return ProfileValidationResult(
            is_valid=False,
            missing_fields=["dob", "citizenship", "education_json", "language_json", "work_json"],
            incomplete_sections=["All sections"],
            recommendations=["Create a profile first by uploading immigration documents"]
        )
    
    missing_fields = []
    incomplete_sections = []
    recommendations = []
    
    # Check required fields for CRS calculation
    required_fields = {
        "dob": "Date of birth",
        "citizenship": "Citizenship",
    }
    
    for field, label in required_fields.items():
        if not profile.get(field):
            missing_fields.append(field)
            recommendations.append(f"Provide {label} for accurate CRS score calculation")
    
    # Check sections needed for CRS
    if not profile.get("education_json"):
        incomplete_sections.append("Education")
        recommendations.append("Upload educational documents (degrees, diplomas) to calculate education points")
    
    if not profile.get("language_json"):
        incomplete_sections.append("Language Proficiency")
        recommendations.append("Upload language test results (IELTS, CELPIP, TEF) to calculate language points")
    
    if not profile.get("work_json"):
        incomplete_sections.append("Work Experience")
        recommendations.append("Upload work experience documents to calculate work experience points")
    
    # Additional recommendations based on permit type
    # Check if user has documents to infer permit type
    documents = await db.documents.find({"user_id": user_id}).to_list(length=100)
    document_types = [doc.get("type_detected") for doc in documents if doc.get("type_detected")]
    
    if "study_permit" in document_types:
        if not profile.get("arrival_date"):
            recommendations.append("Provide arrival date to track study permit validity")
    elif "work_permit" in document_types:
        if not profile.get("work_json"):
            recommendations.append("Work permit holders should provide detailed work experience for CRS calculation")
    
    is_valid = len(missing_fields) == 0 and len(incomplete_sections) == 0
    
    return ProfileValidationResult(
        is_valid=is_valid,
        missing_fields=missing_fields,
        incomplete_sections=incomplete_sections,
        recommendations=recommendations
    )
