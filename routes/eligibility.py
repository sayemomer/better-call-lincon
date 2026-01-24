"""
Eligibility & CRS scoring API.

Implements POST /api/v1/eligibility/crs/compute per SRS 3.3.
Fetches profile from user database and uses CRS agent to compute Express Entry score.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.deps import get_current_user
from app.db import get_db
from models.eligibility import CRSComputeOverrides, CRSComputeResponse\

from app.ai.crs_agent import profile_to_crs_input
from app.ai.crs_dynamic import compute_crs, get_rule_check_status, clear_rule_check_cache

router = APIRouter()


@router.post("/crs/compute", response_model=CRSComputeResponse)
async def crs_compute(
    overrides: CRSComputeOverrides | None = Body(default=None),
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
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
    doc = await db["profiles"].find_one({"user_id": user["_id"]})
    data = dict((doc or {}).get("data", {}))

    if overrides:
        override_dict = overrides.model_dump(exclude_none=True)
        data.update(override_dict)

    inp = profile_to_crs_input(data)
    # Use dynamic calculator (automatically chooses hardcoded or AI)
    result = compute_crs(inp)

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
