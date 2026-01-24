"""
Eligibility & CRS scoring API.

Implements POST /api/v1/eligibility/crs/compute per SRS 3.3.
Fetches profile from user database and uses CRS agent to compute Express Entry score.
"""

from __future__ import annotations

from typing import Any
from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, Request
from bson import ObjectId

from app.auth.deps import get_current_user
from app.db import get_db
from models.eligibility import CRSComputeOverrides, CRSComputeResponse

from app.ai.crs_agent import profile_to_crs_input
from app.ai.crs_dynamic import compute_crs, get_rule_check_status, clear_rule_check_cache
from app.utils.crs_requirements import analyze_crs_requirements

router = APIRouter()


@router.post("/crs/compute", response_model=CRSComputeResponse)
async def crs_compute(
    request: Request,
    overrides: CRSComputeOverrides | None = Body(default=None),
    user: dict = Depends(get_current_user),
) -> CRSComputeResponse:
    """
    Compute Express Entry CRS score from the user's profile.

    Profile data is read from the database. Optional request body fields
    override or supplement profile data for this computation only.
    Send `{}` when using only profile data.

    CRS criteria follow the official [Canada.ca calculator](https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/check-score.html).
    Job offer points are not awarded (removed March 2025).
    
    The system automatically checks if CRS rules have changed and uses AI-based calculation
    if rules differ from the hardcoded implementation. This ensures accuracy even when
    IRCC updates the scoring system.
    """
    db = get_db(request)
    user_id = ObjectId(user["id"])
    doc = await db.profiles.find_one({"user_id": user_id})
    
    # Get data from profile.data, but also check root profile fields
    data = dict((doc or {}).get("data", {}))
    
    # Merge root profile fields into data (for backward compatibility)
    if doc:
        # DOB - can be in root or data
        if not data.get("dob") and doc.get("dob"):
            dob_val = doc.get("dob")
            # Convert datetime to string if needed
            if isinstance(dob_val, datetime):
                data["dob"] = dob_val.date().isoformat()
            elif isinstance(dob_val, date):
                data["dob"] = dob_val.isoformat()
            else:
                data["dob"] = str(dob_val)
        
        # Marital status - default to "single" if null/empty
        if not data.get("marital_status") and doc.get("marital_status"):
            data["marital_status"] = doc.get("marital_status")
        elif not data.get("marital_status"):
            # Default to single if not provided (passport doesn't show marriage = unmarried)
            data["marital_status"] = "single"
        
        # Education - merge from education_json if individual fields not present
        if doc.get("education_json") and isinstance(doc.get("education_json"), dict):
            edu_json = doc.get("education_json")
            if not data.get("education_level") and edu_json.get("education_level"):
                data["education_level"] = edu_json.get("education_level")
            if not data.get("education_level_detail") and edu_json.get("education_level_detail"):
                data["education_level_detail"] = edu_json.get("education_level_detail")
            if data.get("canadian_education") is None and edu_json.get("canadian_education") is not None:
                data["canadian_education"] = edu_json.get("canadian_education")
        
        # Calculate age from DOB if age is not provided
        if not data.get("age") and data.get("dob"):
            try:
                dob_str = data["dob"]
                dob_date = None
                
                if isinstance(dob_str, str):
                    # Try to parse various date formats
                    try:
                        # Try ISO format first (handles timezone)
                        dob_date = datetime.fromisoformat(dob_str.replace("Z", "+00:00")).date()
                    except:
                        try:
                            # Try YYYY-MM-DD format (most common)
                            dob_date = datetime.strptime(dob_str, "%Y-%m-%d").date()
                        except:
                            # Try other common formats
                            for fmt in ["%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y", "%m-%d-%Y"]:
                                try:
                                    dob_date = datetime.strptime(dob_str, fmt).date()
                                    break
                                except:
                                    continue
                elif isinstance(dob_str, datetime):
                    dob_date = dob_str.date()
                elif isinstance(dob_str, date):
                    dob_date = dob_str
                
                if dob_date:
                    today = date.today()
                    age_calculated = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
                    if age_calculated > 0 and age_calculated < 120:
                        data["age"] = age_calculated
            except Exception as e:
                # Log error for debugging but don't fail
                print(f"Error calculating age from DOB: {str(e)}")
                pass
    
    # Check if we have minimum requirements (warn but allow calculation with partial data)
    crs_analysis = analyze_crs_requirements(data)
    
    if overrides:
        override_dict = overrides.model_dump(exclude_none=True)
        data.update(override_dict)
        # Re-analyze after overrides
        crs_analysis = analyze_crs_requirements(data)
    
    inp = profile_to_crs_input(data)
    # Use dynamic calculator (automatically chooses hardcoded or AI)
    # Note: Calculator can work with partial data, but will show missing fields
    result = compute_crs(inp)
    
    # Add requirement analysis to breakdown
    can_calculate = crs_analysis.get("can_calculate", False)
    is_complete = crs_analysis.get("is_complete", False)
    
    if not can_calculate:
        result.breakdown["requirements_status"] = {
            "can_calculate": False,
            "is_complete": False,
            "missing_required_fields": crs_analysis["missing_required"],
            "missing_optional_fields": crs_analysis["missing_optional"],
            "message": "Cannot calculate meaningful CRS score. Missing required fields. Please upload: passport (for age), education documents, and language test results."
        }
        # Set total to 0 and add warning
        result.total = 0
        result.missing_or_defaulted.extend(crs_analysis["missing_required"])
    elif not is_complete:
        result.breakdown["requirements_status"] = {
            "can_calculate": True,
            "is_complete": False,
            "missing_required_fields": [],  # All required are present
            "missing_optional_fields": crs_analysis["missing_optional"],
            "message": "CRS calculated with minimum required fields. Upload additional documents to improve score."
        }
    else:
        result.breakdown["requirements_status"] = {
            "can_calculate": True,
            "is_complete": True,
            "missing_required_fields": [],
            "missing_optional_fields": [],
            "message": "All required fields present. Complete CRS calculation available."
        }

    return CRSComputeResponse(
        total=result.total,
        core_human_capital=result.core_human_capital,
        spouse_factors=result.spouse_factors,
        skill_transferability=result.skill_transferability,
        additional_points=result.additional_points,
        breakdown=result.breakdown,
        missing_or_defaulted=result.missing_or_defaulted,
        disclaimer=result.disclaimer,
    )


@router.get("/crs/rule-status")
async def get_crs_rule_status() -> dict[str, Any]:
    """
    Get the status of CRS rule checking.
    
    Shows whether hardcoded rules match official rules and which calculation
    method is currently being used.
    """
    return get_rule_check_status()


@router.post("/crs/refresh-rules")
async def refresh_crs_rules(
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Force a fresh check of CRS rules against official sources.
    
    Clears the cache and checks if rules have changed. Requires authentication.
    """
    clear_rule_check_cache()
    status = get_rule_check_status()
    return {
        "message": "Rule check cache cleared. Next CRS calculation will use fresh rule check.",
        "status": status,
    }
