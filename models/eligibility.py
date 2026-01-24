"""Schemas for eligibility and CRS compute API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CRSComputeResponse(BaseModel):
    """Response for POST /eligibility/crs/compute."""

    total: int = Field(..., description="Total CRS score (max 1200)")
    core_human_capital: int = Field(..., description="Points from age, education, language, Canadian work")
    spouse_factors: int = Field(0, description="Points from spouse education, work, language")
    skill_transferability: int = Field(0, description="Points from education+language, education+work, foreign work+language")
    additional_points: int = Field(0, description="Provincial nomination, Canadian study, sibling, etc.")
    breakdown: dict = Field(default_factory=dict, description="Per-factor point breakdown")
    missing_or_defaulted: list[str] = Field(default_factory=list, description="Profile fields missing or defaulted")
    disclaimer: str = Field(
        default="This tool is for general guidance only. Official IRCC system results govern. See Canada.ca Express Entry CRS calculator. Not legal advice.",
        description="Legal disclaimer",
    )


class CRSComputeOverrides(BaseModel):
    """
    Optional overrides when computing CRS.
    If provided, these are merged with profile data from the database.
    """

    age: int | None = None
    marital_status: str | None = None
    spouse_accompanying: bool | None = None
    education_level: str | None = None
    education_level_detail: str | None = None
    canadian_education: bool | None = None
    language_scores: dict | None = None
    canadian_work_years: int | None = None
    foreign_work_years: int | None = None
    certificate_of_qualification: bool | None = None
    provincial_nomination: bool | None = None
    sibling_in_canada: bool | None = None
