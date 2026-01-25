"""
CRS Rule Checker Agent - Validates hardcoded implementation against official rules.

This agent:
1. Fetches/checks the official CRS criteria from Canada.ca
2. Compares with hardcoded implementation
3. Detects if rules have changed
4. Returns a decision on whether to use hardcoded or AI-based calculation
"""

from __future__ import annotations

import json
import os
import hashlib
from dataclasses import dataclass
from typing import Any
from datetime import datetime

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    from crewai import Agent, Task, Crew, Process, LLM
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False


@dataclass
class CRSRuleCheckResult:
    """Result of CRS rule validation check."""
    rules_match: bool
    use_hardcoded: bool
    changes_detected: list[str]
    official_rules_summary: dict[str, Any] | None
    last_checked: datetime
    error: str | None = None


# Known CRS rule signature (hash of key rules) - UPDATE THIS when IRCC changes rules
# 
# To update when rules change:
# 1. Check official Canada.ca CRS criteria page
# 2. Update the values below to match new rules
# 3. The system will automatically detect the change and use AI-based calculation
# 4. After verifying AI calculation is correct, update hardcoded implementation in crs_agent.py
#
KNOWN_CRS_RULES_SIGNATURE = {
    "job_offer_points": "removed_2025_03_25",  # Job offers removed March 25, 2025
    "max_points": 1200,
    "core_max_single": 500,
    "core_max_spouse": 460,
    "age_max_single": 110,
    "age_max_spouse": 100,
    "education_max_single": 150,
    "education_max_spouse": 140,
    "language_max_single": 160,
    "language_max_spouse": 150,
    "canadian_work_max_single": 80,
    "canadian_work_max_spouse": 70,
    "provincial_nomination": 600,
    "canadian_study_1_2yr": 15,
    "canadian_study_3plus": 30,
    "sibling": 15,
    "certificate_qualification": 50,
    "second_language": 6,
}


def _get_rules_signature_hash() -> str:
    """Generate hash of known rules signature for comparison."""
    rules_str = json.dumps(KNOWN_CRS_RULES_SIGNATURE, sort_keys=True)
    return hashlib.sha256(rules_str.encode()).hexdigest()[:16]


def _fetch_crs_criteria_page() -> str | None:
    """Fetch the official CRS criteria page from Canada.ca."""
    if not HTTPX_AVAILABLE:
        return None
    
    urls = [
        "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/check-score/crs-criteria.html",
        "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/check-score.html",
    ]
    
    for url in urls:
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, follow_redirects=True)
                if response.status_code == 200:
                    return response.text
        except Exception:
            continue
    
    return None


def _extract_rules_summary_with_ai(page_content: str | None) -> dict[str, Any] | None:
    """Use AI agent to extract CRS rules summary from page content or web search."""
    if not CREWAI_AVAILABLE:
        return None
    
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_api_key:
        return None
    
    model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
    llm = LLM(model=model, api_key=openrouter_api_key, base_url="https://openrouter.ai/api/v1")
    
    agent = Agent(
        role="CRS Rules Analyst",
        goal="Extract and summarize current CRS (Comprehensive Ranking System) scoring rules from official sources.",
        backstory=(
            "You are an expert at analyzing Canadian immigration CRS criteria. "
            "You extract key point values, maximums, and rule changes from official IRCC documentation. "
            "You focus on: age points, education points, language points, work experience points, "
            "provincial nomination, Canadian study bonus, sibling points, and any recent changes."
        ),
        llm=llm,
        verbose=False,
    )
    
    task_description = (
        "Extract the current CRS (Comprehensive Ranking System) scoring rules from the official Canada.ca pages.\n\n"
        "Focus on these key areas:\n"
        "1. Maximum points (should be 1200)\n"
        "2. Core human capital factors:\n"
        "   - Age points (max for single vs with spouse)\n"
        "   - Education points (max for single vs with spouse)\n"
        "   - Language points (max for single vs with spouse)\n"
        "   - Canadian work experience points (max for single vs with spouse)\n"
        "3. Additional points:\n"
        "   - Provincial nomination (should be 600)\n"
        "   - Canadian study bonus (1-2 year vs 3+ year)\n"
        "   - Sibling in Canada (should be 15)\n"
        "   - Certificate of qualification (should be 50)\n"
        "   - Second official language (should be 6)\n"
        "4. Recent changes:\n"
        "   - Job offer points (removed March 25, 2025?)\n"
        "   - Any other rule changes\n\n"
    )
    
    if page_content:
        task_description += f"Page content snippet:\n{page_content[:5000]}\n\n"
    else:
        task_description += (
            "If page content is not available, use your knowledge of current CRS rules "
            "and check for any recent changes. You can also reference:\n"
            "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/check-score.html\n\n"
        )
    
    task_description += (
        "Output STRICT JSON ONLY:\n"
        '{\n'
        '  "max_points": 1200,\n'
        '  "core_max_single": 500,\n'
        '  "core_max_spouse": 460,\n'
        '  "age_max_single": 110,\n'
        '  "age_max_spouse": 100,\n'
        '  "education_max_single": 150,\n'
        '  "education_max_spouse": 140,\n'
        '  "language_max_single": 160,\n'
        '  "language_max_spouse": 150,\n'
        '  "canadian_work_max_single": 80,\n'
        '  "canadian_work_max_spouse": 70,\n'
        '  "provincial_nomination": 600,\n'
        '  "canadian_study_1_2yr": 15,\n'
        '  "canadian_study_3plus": 30,\n'
        '  "sibling": 15,\n'
        '  "certificate_qualification": 50,\n'
        '  "second_language": 6,\n'
        '  "job_offer_points": "removed" or number,\n'
        '  "recent_changes": ["list of any changes"],\n'
        '  "rules_match_hardcoded": true/false\n'
        '}\n'
    )
    
    task = Task(
        description=task_description,
        expected_output="A strict JSON object with CRS rules summary and comparison.",
        agent=agent,
    )
    
    try:
        crew = Crew(process=Process.sequential, agents=[agent], tasks=[task])
        result = crew.kickoff()
        raw = result.raw if hasattr(result, "raw") else str(result)
        
        # Parse JSON
        try:
            data = json.loads(raw)
            return data
        except json.JSONDecodeError:
            # Try to extract JSON from text
            import re
            json_match = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
    except Exception as e:
        return None
    
    return None


def _compare_rules(hardcoded: dict[str, Any], official: dict[str, Any] | None) -> tuple[bool, list[str]]:
    """Compare hardcoded rules with official rules. Returns (match, changes_detected)."""
    if not official:
        # If we can't fetch official rules, assume they match (use hardcoded)
        return True, []
    
    changes = []
    
    # Compare key values
    for key in KNOWN_CRS_RULES_SIGNATURE:
        hardcoded_val = hardcoded.get(key)
        official_val = official.get(key)
        
        if official_val is None:
            continue  # Skip if not in official
        
        if hardcoded_val != official_val:
            changes.append(f"{key}: hardcoded={hardcoded_val}, official={official_val}")
    
    # Check for job offer points
    job_offer = official.get("job_offer_points")
    if job_offer and job_offer != "removed" and job_offer != 0:
        changes.append(f"job_offer_points: expected removed/0, got {job_offer}")
    
    # Check recent changes
    recent_changes = official.get("recent_changes", [])
    if recent_changes:
        changes.append(f"Recent changes reported: {', '.join(recent_changes)}")
    
    return len(changes) == 0, changes


def check_crs_rules(force_check: bool = False) -> CRSRuleCheckResult:
    """
    Check if hardcoded CRS rules match official rules.
    
    Args:
        force_check: If True, always fetch and check. If False, may use cached result.
    
    Returns:
        CRSRuleCheckResult with decision on whether to use hardcoded implementation.
    """
    try:
        # Fetch official page
        page_content = _fetch_crs_criteria_page() if force_check or HTTPX_AVAILABLE else None
        
        # Extract rules with AI
        official_rules = _extract_rules_summary_with_ai(page_content)
        
        # Compare
        rules_match, changes = _compare_rules(KNOWN_CRS_RULES_SIGNATURE, official_rules)
        
        return CRSRuleCheckResult(
            rules_match=rules_match,
            use_hardcoded=rules_match,  # Use hardcoded if rules match
            changes_detected=changes,
            official_rules_summary=official_rules,
            last_checked=datetime.utcnow(),
            error=None,
        )
    except Exception as e:
        # On error, default to using hardcoded (safer)
        return CRSRuleCheckResult(
            rules_match=True,  # Assume match on error
            use_hardcoded=True,
            changes_detected=[],
            official_rules_summary=None,
            last_checked=datetime.utcnow(),
            error=str(e),
        )
