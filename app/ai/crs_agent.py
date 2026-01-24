"""
CRS (Comprehensive Ranking System) scoring agent for Express Entry.

Computes CRS scores based on the official IRCC calculator and criteria:
https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/check-score.html

As of March 25, 2025, job offer points are no longer awarded. Job offers
still affect eligibility for some programs but not CRS score.

Legal disclaimer: This tool is for general guidance only. Official IRCC
system results govern. See Canada.ca CRS calculator disclaimer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

# --- Language test → CLB conversion ---
# IELTS General: standard IRCC conversion. 6.0→7, 6.5→8, 7.0→9, 7.5→9, 8.0→10, 8.5→10, 9→12
def _ielts_to_clb(score: float | None) -> int:
    if score is None:
        return 0
    s = float(score)
    if s <= 3.0:
        return 4
    if s <= 3.5:
        return 4
    if s <= 4.0:
        return 5
    if s <= 4.5:
        return 5
    if s <= 5.0:
        return 6
    if s <= 5.5:
        return 6
    if s <= 6.0:
        return 7
    if s <= 6.5:
        return 8
    if s <= 7.0:
        return 9
    if s <= 7.5:
        return 9
    if s <= 8.0:
        return 10
    if s <= 8.5:
        return 10
    return 12


def _clb_from_scores(
    test_type: str,
    speaking: float | None,
    listening: float | None,
    reading: float | None,
    writing: float | None,
) -> tuple[int, int, int, int]:
    """Convert test scores to CLB (S, L, R, W). Supports IELTS, CELPIP-G, PTE Core."""
    if test_type and "celpip" in test_type.lower():
        def _c(s: float | None) -> int:
            if s is None:
                return 0
            try:
                v = int(float(s))
                return v if 1 <= v <= 12 else 0
            except (TypeError, ValueError):
                return 0
        return (_c(speaking), _c(listening), _c(reading), _c(writing))
    if test_type and "pte" in test_type.lower():
        def _p(s: float | None) -> int:
            if s is None:
                return 0
            try:
                v = float(s)
            except (TypeError, ValueError):
                return 0
            if v < 36:
                return 4
            if v < 47:
                return 5
            if v < 55:
                return 6
            if v < 63:
                return 7
            if v < 75:
                return 8
            if v < 83:
                return 9
            return 10
        return (_p(speaking), _p(listening), _p(reading), _p(writing))
    return (
        _ielts_to_clb(speaking),
        _ielts_to_clb(listening),
        _ielts_to_clb(reading),
        _ielts_to_clb(writing),
    )


# First official language: points per skill by CLB (single, with_spouse)
def _lang_points(clb: int, with_spouse: bool) -> int:
    grid = {
        4: (0, 0), 5: (1, 1), 6: (9, 8), 7: (17, 15), 8: (23, 21),
        9: (31, 29), 10: (34, 32), 11: (34, 32), 12: (34, 32),
    }
    single_pts, spouse_pts = grid.get(clb, (0, 0))
    return spouse_pts if with_spouse else single_pts


# Second official language: 6 points total (with spouse) or 6 per skill? Usually 6 max.
def _second_lang_points(clb_min: int) -> int:
    if clb_min >= 5:
        return 6
    return 0


# Age points: single vs with spouse
def _age_points(age: int, with_spouse: bool) -> int:
    if age < 18:
        return 0
    if age >= 45:
        return 0
    # Single
    single = {18: 99, 19: 105}
    if age <= 19:
        base = single.get(age, 0)
        return base if not with_spouse else max(0, base - 10)
    if age <= 29:
        return 110 if not with_spouse else 100
    # 30–44
    decline = [105, 99, 93, 87, 81, 75, 69, 63, 57, 51, 45, 39, 33, 27, 21, 15]
    idx = min(age - 30, 15)
    pt = decline[idx] if idx < len(decline) else 0
    if with_spouse:
        pt = max(0, pt - 10)
    return pt


# Education (principal) – single / with spouse
def _education_points(level: str, with_spouse: bool) -> int:
    levels = {
        "secondary": (30, 28),
        "one_two_year_diploma": (90, 84),  # 1-2 year
        "two_year_diploma": (98, 91),
        "bachelors": (120, 112),
        "two_or_more": (128, 119),  # two or more, one 3+ yr
        "masters": (135, 126),
        "phd": (150, 140),
    }
    key = (level or "").strip().lower().replace(" ", "_")
    for k, (s, w) in levels.items():
        if k in key or key in k:
            return w if with_spouse else s
    if "bachelor" in key or "degree" in key or "3" in key:
        return 112 if with_spouse else 120
    if "master" in key or "masters" in key:
        return 126 if with_spouse else 135
    if "phd" in key or "doctoral" in key:
        return 140 if with_spouse else 150
    if "diploma" in key or "1" in key or "2" in key:
        return 91 if with_spouse else 98
    return 28 if with_spouse else 30  # default secondary


# Canadian work experience – single / with spouse
def _canadian_work_points(years: int, with_spouse: bool) -> int:
    grid = [(0, 0), (40, 35), (53, 46), (64, 56), (72, 63), (80, 70)]
    idx = min(max(0, years), 5)
    s, w = grid[idx]
    return w if with_spouse else s


# Spouse: education, Canadian work, language
def _spouse_education_points(level: str) -> int:
    levels = {
        "none": 0, "secondary": 2, "one_year": 6, "two_year": 7,
        "bachelors": 8, "two_or_more": 9, "masters": 10, "phd": 10,
    }
    key = (level or "").strip().lower()
    for k, v in levels.items():
        if k in key:
            return v
    return 0


def _spouse_canadian_work_points(years: int) -> int:
    grid = [0, 5, 7, 8, 9, 10]
    return grid[min(max(0, years), 5)]


def _spouse_language_points(clb_min: int) -> int:
    if clb_min >= 9:
        return 5
    if clb_min >= 5:
        return 1
    return 0


# Skill transferability (simplified): education+language, education+Canadian work, foreign work+language
def _transferability_education_language(
    edu_level: str, clb_min: int, with_spouse: bool
) -> int:
    if clb_min >= 9 and edu_level in ("masters", "phd", "two_or_more", "bachelors"):
        return 50 if not with_spouse else 50
    if clb_min >= 7 and edu_level in ("masters", "phd", "two_or_more", "bachelors"):
        return 25 if not with_spouse else 25
    return 0


def _transferability_education_canadian_work(
    edu_level: str, canadian_years: int, with_spouse: bool
) -> int:
    if canadian_years >= 2 and edu_level in ("masters", "phd", "two_or_more", "bachelors"):
        return 50 if not with_spouse else 50
    if canadian_years >= 1 and edu_level in ("masters", "phd", "two_or_more", "bachelors"):
        return 25 if not with_spouse else 25
    return 0


def _transferability_foreign_language(foreign_years: int, clb_min: int) -> int:
    if foreign_years >= 3 and clb_min >= 9:
        return 50
    if foreign_years >= 3 and clb_min >= 7:
        return 25
    if foreign_years >= 1 and clb_min >= 9:
        return 25
    if foreign_years >= 1 and clb_min >= 7:
        return 13
    return 0


# Canadian study bonus
def _canadian_study_bonus(has_canadian_edu: bool, level_detail: str) -> int:
    if not has_canadian_edu:
        return 0
    ld = (level_detail or "").lower()
    if "secondary" in ld or "1" in ld or "2" in ld or "one" in ld or "two" in ld:
        return 15
    return 30  # 3+ year degree, master, PhD


@dataclass
class CRSInput:
    """Normalized input for CRS computation (maps from profile data)."""

    age: int = 0
    marital_status: str = "single"
    spouse_accompanying: bool = False
    spouse_canadian_pr: bool = False
    education_level: str = ""
    education_level_detail: str = ""
    canadian_education: bool = False
    language_test: str = "ielts"
    lang_speaking: float | None = None
    lang_listening: float | None = None
    lang_reading: float | None = None
    lang_writing: float | None = None
    has_second_language: bool = False
    second_lang_speaking: float | None = None
    second_lang_listening: float | None = None
    second_lang_reading: float | None = None
    second_lang_writing: float | None = None
    canadian_work_years: int = 0
    foreign_work_years: int = 0
    certificate_of_qualification: bool = False
    provincial_nomination: bool = False
    sibling_in_canada: bool = False
    # Spouse (if accompanying)
    spouse_education_level: str = ""
    spouse_canadian_work_years: int = 0
    spouse_lang_speaking: float | None = None
    spouse_lang_listening: float | None = None
    spouse_lang_reading: float | None = None
    spouse_lang_writing: float | None = None
    spouse_language_test: str = "ielts"


@dataclass
class CRSResult:
    """CRS computation result with breakdown."""

    total: int = 0
    core_human_capital: int = 0
    spouse_factors: int = 0
    skill_transferability: int = 0
    additional_points: int = 0
    breakdown: dict[str, Any] = field(default_factory=dict)
    missing_or_defaulted: list[str] = field(default_factory=list)
    disclaimer: str = (
        "This tool is for general guidance only. Official IRCC system results govern. "
        "See Canada.ca Express Entry CRS calculator. Not legal advice."
    )


def _normalize_edu_level(level: str) -> str:
    s = (level or "").strip().lower()
    if "phd" in s or "doctoral" in s:
        return "phd"
    if "master" in s or "masters" in s:
        return "masters"
    if "bachelor" in s or "degree" in s or "3" in s:
        return "bachelors"
    if "two_or_more" in s or "two or more" in s:
        return "two_or_more"
    if "diploma" in s or "1" in s or "2" in s:
        return "two_year_diploma"
    return "secondary"


def compute_crs(inp: CRSInput) -> CRSResult:
    """
    Compute CRS score from normalized input.

    Implements the Comprehensive Ranking System based on the official
    Canada.ca calculator and CRS criteria. Job offer points are not
    awarded (removed March 2025).
    """
    missing: list[str] = []
    if inp.age <= 0:
        missing.append("age")
    if not inp.education_level and not inp.education_level_detail:
        missing.append("education_level")

    with_spouse = inp.spouse_accompanying and inp.marital_status not in (
        "single", "never_married", "divorced", "widowed", "separated", "annulled"
    )
    # Treat "married" or "common_law" with accompanying spouse
    if inp.marital_status.lower() in ("married", "common_law", "common-law") and inp.spouse_accompanying:
        with_spouse = True

    # --- Core: age ---
    age_pts = _age_points(inp.age, with_spouse) if inp.age > 0 else 0

    # --- Core: education ---
    edu_norm = _normalize_edu_level(inp.education_level or inp.education_level_detail)
    edu_pts = _education_points(edu_norm, with_spouse)

    # --- Core: first official language ---
    s, l, r, w = _clb_from_scores(
        inp.language_test,
        inp.lang_speaking, inp.lang_listening, inp.lang_reading, inp.lang_writing,
    )
    clb_min = min(x for x in (s, l, r, w) if x > 0) if (s or l or r or w) else 0
    has_lang = any(x is not None for x in (inp.lang_speaking, inp.lang_listening, inp.lang_reading, inp.lang_writing))
    if not has_lang:
        missing.append("language_scores")
    lang_pts = sum(_lang_points(x, with_spouse) for x in (s, l, r, w)) if clb_min > 0 else 0

    # --- Core: Canadian work ---
    cdn_work_pts = _canadian_work_points(inp.canadian_work_years, with_spouse)

    core = age_pts + edu_pts + lang_pts + cdn_work_pts

    # --- Spouse factors ---
    spouse_pts = 0
    if with_spouse:
        spouse_pts += _spouse_education_points(inp.spouse_education_level)
        spouse_pts += _spouse_canadian_work_points(inp.spouse_canadian_work_years)
        ss, sl, sr, sw = _clb_from_scores(
            inp.spouse_language_test,
            inp.spouse_lang_speaking, inp.spouse_lang_listening,
            inp.spouse_lang_reading, inp.spouse_lang_writing,
        )
        spouse_clb = min(x for x in (ss, sl, sr, sw) if x > 0) if any((ss, sl, sr, sw)) else 0
        spouse_pts += _spouse_language_points(spouse_clb)

    # --- Skill transferability ---
    trans_edu_lang = _transferability_education_language(edu_norm, clb_min, with_spouse)
    trans_edu_work = _transferability_education_canadian_work(
        edu_norm, inp.canadian_work_years, with_spouse
    )
    trans_foreign = _transferability_foreign_language(inp.foreign_work_years, clb_min)
    transferability = min(100, trans_edu_lang + trans_edu_work + trans_foreign)

    # --- Additional ---
    add = 0
    if inp.provincial_nomination:
        add += 600
    add += _canadian_study_bonus(inp.canadian_education, inp.education_level_detail)
    if inp.sibling_in_canada:
        add += 15
    if inp.certificate_of_qualification:
        add += 50
    # Second official language (French/English)
    if inp.has_second_language:
        s2, l2, r2, w2 = _clb_from_scores(
            "ielts",
            inp.second_lang_speaking, inp.second_lang_listening,
            inp.second_lang_reading, inp.second_lang_writing,
        )
        clb2 = min(x for x in (s2, l2, r2, w2) if x > 0) if any((s2, l2, r2, w2)) else 0
        add += _second_lang_points(clb2)
    # Job offer: 0 (removed March 2025)

    total = core + spouse_pts + transferability + add
    total = min(1200, total)

    breakdown = {
        "age": age_pts,
        "education": edu_pts,
        "first_official_language": lang_pts,
        "canadian_work_experience": cdn_work_pts,
        "spouse_factors": spouse_pts,
        "skill_transferability": transferability,
        "provincial_nomination": 600 if inp.provincial_nomination else 0,
        "canadian_study_bonus": _canadian_study_bonus(inp.canadian_education, inp.education_level_detail),
        "sibling_in_canada": 15 if inp.sibling_in_canada else 0,
        "certificate_of_qualification": 50 if inp.certificate_of_qualification else 0,
        "second_official_language": 6 if inp.has_second_language and (
            min(_clb_from_scores("ielts",
                inp.second_lang_speaking, inp.second_lang_listening,
                inp.second_lang_reading, inp.second_lang_writing)) >= 5
        ) else 0,
    }

    return CRSResult(
        total=total,
        core_human_capital=core,
        spouse_factors=spouse_pts,
        skill_transferability=transferability,
        additional_points=add,
        breakdown=breakdown,
        missing_or_defaulted=missing,
    )


def profile_to_crs_input(data: dict[str, Any]) -> CRSInput:
    """
    Map profile `data` (from user profile document) to CRSInput.

    Expected profile keys (snake_case or camelCase):
    - age (int)
    - marital_status, spouse_accompanying, spouse_canadian_pr
    - education_level, education_level_detail, canadian_education
    - language_scores: { test, speaking, listening, reading, writing }
    - second_language_scores (optional)
    - canadian_work_years, foreign_work_years
    - certificate_of_qualification, provincial_nomination, sibling_in_canada
    - spouse_* (if applicable)
    """
    def _int(v: Any, default: int = 0) -> int:
        if v is None:
            return default
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return default

    def _float(v: Any):
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    def _bool(v: Any) -> bool:
        if v is None:
            return False
        if isinstance(v, bool):
            return v
        return str(v).strip().lower() in ("1", "true", "yes", "y")

    def _str(v: Any) -> str:
        return str(v).strip() if v is not None else ""

    lang = data.get("language_scores") or data.get("languageScores") or {}
    if isinstance(lang, list) and lang:
        lang = lang[0]
    spouse_lang = data.get("spouse_language_scores") or data.get("spouseLanguageScores") or {}
    if isinstance(spouse_lang, list) and spouse_lang:
        spouse_lang = spouse_lang[0]

    age_val = _int(data.get("age") or data.get("dob_age"))
    if age_val <= 0 and data.get("dob"):
        try:
            d = data["dob"]
            if isinstance(d, str):
                d = datetime.fromisoformat(d.replace("Z", "+00:00")).date()
            elif isinstance(d, datetime):
                d = d.date()
            if isinstance(d, date):
                today = date.today()
                age_val = today.year - d.year - ((today.month, today.day) < (d.month, d.day))
        except Exception:
            pass

    s2lang = data.get("second_language_scores") or data.get("secondLanguageScores") or {}
    if isinstance(s2lang, list) and s2lang:
        s2lang = s2lang[0]

    return CRSInput(
        age=age_val,
        marital_status=_str(data.get("marital_status") or data.get("maritalStatus") or "single"),
        spouse_accompanying=_bool(data.get("spouse_accompanying") or data.get("spouseAccompanying")),
        spouse_canadian_pr=_bool(data.get("spouse_canadian_pr") or data.get("spouseCanadianPr")),
        education_level=_str(data.get("education_level") or data.get("educationLevel")),
        education_level_detail=_str(data.get("education_level_detail") or data.get("educationLevelDetail")),
        canadian_education=_bool(data.get("canadian_education") or data.get("canadianEducation")),
        language_test=_str(lang.get("test") or lang.get("testType") or "ielts"),
        lang_speaking=_float(lang.get("speaking")),
        lang_listening=_float(lang.get("listening")),
        lang_reading=_float(lang.get("reading")),
        lang_writing=_float(lang.get("writing")),
        has_second_language=_bool(data.get("has_second_language") or data.get("hasSecondLanguage")),
        second_lang_speaking=_float(s2lang.get("speaking")),
        second_lang_listening=_float(s2lang.get("listening")),
        second_lang_reading=_float(s2lang.get("reading")),
        second_lang_writing=_float(s2lang.get("writing")),
        canadian_work_years=_int(data.get("canadian_work_years") or data.get("canadianWorkYears")),
        foreign_work_years=_int(data.get("foreign_work_years") or data.get("foreignWorkYears")),
        certificate_of_qualification=_bool(data.get("certificate_of_qualification") or data.get("certificateOfQualification")),
        provincial_nomination=_bool(data.get("provincial_nomination") or data.get("provincialNomination")),
        sibling_in_canada=_bool(data.get("sibling_in_canada") or data.get("siblingInCanada")),
        spouse_education_level=_str(data.get("spouse_education_level") or data.get("spouseEducationLevel")),
        spouse_canadian_work_years=_int(data.get("spouse_canadian_work_years") or data.get("spouseCanadianWorkYears")),
        spouse_lang_speaking=_float(spouse_lang.get("speaking")),
        spouse_lang_listening=_float(spouse_lang.get("listening")),
        spouse_lang_reading=_float(spouse_lang.get("reading")),
        spouse_lang_writing=_float(spouse_lang.get("writing")),
        spouse_language_test=_str(spouse_lang.get("test") or spouse_lang.get("testType") or "ielts"),
    )
