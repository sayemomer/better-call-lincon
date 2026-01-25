"""
Dynamic CRS Calculator - Automatically chooses between hardcoded and AI-based calculation.

This module:
1. Checks if hardcoded rules match official rules
2. Uses hardcoded implementation if rules match (faster, more reliable)
3. Falls back to AI-based calculation if rules have changed
4. Caches rule check results to avoid repeated checks
"""

from __future__ import annotations

import os
import logging
from datetime import datetime, timedelta
from typing import Any

from app.ai.crs_agent import CRSInput, CRSResult, compute_crs as compute_crs_hardcoded
from app.ai.crs_rule_checker import check_crs_rules, CRSRuleCheckResult
from app.ai.crs_ai_calculator import compute_crs_with_ai

logger = logging.getLogger(__name__)

# Cache rule check results (check once per hour by default)
_rule_check_cache: CRSRuleCheckResult | None = None
_cache_timestamp: datetime | None = None
CACHE_DURATION = timedelta(hours=1)


def _should_refresh_cache(force_check: bool = False) -> bool:
    """Determine if rule check cache should be refreshed."""
    if force_check:
        return True
    if _rule_check_cache is None or _cache_timestamp is None:
        return True
    if datetime.utcnow() - _cache_timestamp > CACHE_DURATION:
        return True
    return False


def _get_rule_check(force_check: bool = False) -> CRSRuleCheckResult:
    """Get rule check result, using cache if available and fresh."""
    global _rule_check_cache, _cache_timestamp
    
    if _should_refresh_cache(force_check):
        _rule_check_cache = check_crs_rules(force_check=force_check)
        _cache_timestamp = datetime.utcnow()
    
    return _rule_check_cache


def compute_crs(
    inp: CRSInput,
    force_rule_check: bool = False,
    force_ai_calculation: bool = False,
    force_hardcoded: bool = False,
) -> CRSResult:
    """
    Compute CRS score using dynamic method selection.
    
    Args:
        inp: CRS input data
        force_rule_check: Force a fresh rule check (ignore cache)
        force_ai_calculation: Force AI-based calculation (skip rule check)
        force_hardcoded: Force hardcoded calculation (most deterministic, ignores rule check)
    
    Returns:
        CRSResult with score and breakdown
    """
    # If forced to use hardcoded, skip all checks (most deterministic)
    if force_hardcoded:
        logger.info("CRS calculation: Using hardcoded method (forced)")
        result = compute_crs_hardcoded(inp)
        result.breakdown["calculation_method"] = "hardcoded_forced"
        return result
    # If forced to use AI, skip rule check
    if force_ai_calculation:
        logger.info("CRS calculation: Using AI method (forced)")
        try:
            rule_check = _get_rule_check(force_check=True)
            official_rules = rule_check.official_rules_summary
        except Exception:
            official_rules = None
        
        return compute_crs_with_ai(inp, official_rules)
    
    # Check rules (use cache if available)
    try:
        rule_check = _get_rule_check(force_check=force_rule_check)
        logger.info(f"CRS rule check: rules_match={rule_check.rules_match}, use_hardcoded={rule_check.use_hardcoded}, changes_detected={len(rule_check.changes_detected)}")
    except Exception as e:
        # On error, default to hardcoded (safer and more deterministic)
        logger.warning(f"CRS rule check failed: {e}, defaulting to hardcoded calculation")
        result = compute_crs_hardcoded(inp)
        result.breakdown["calculation_method"] = "hardcoded_error_fallback"
        return result
    
    # Decision: use hardcoded if rules match, otherwise use AI
    # IMPORTANT: Prefer hardcoded for determinism. Only use AI if rules definitely changed.
    # Default to hardcoded unless we have clear evidence rules changed
    if rule_check.use_hardcoded or not rule_check.changes_detected or len(rule_check.changes_detected) == 0:
        # Use fast hardcoded implementation (deterministic)
        logger.info("CRS calculation: Using hardcoded method (rules match)")
        result = compute_crs_hardcoded(inp)
        # Add metadata about calculation method
        result.breakdown["calculation_method"] = "hardcoded"
        if rule_check.changes_detected:
            result.breakdown["rule_check_warning"] = "Rules may have changed, but using hardcoded implementation"
        return result
    elif rule_check.error or not rule_check.rules_match:
        # If rule check failed or rules don't match, prefer hardcoded for determinism
        # unless we're certain rules changed
        if not rule_check.changes_detected or len(rule_check.changes_detected) == 0:
            # No clear changes detected, use hardcoded (more deterministic)
            logger.info("CRS calculation: Using hardcoded method (rule check uncertain)")
            result = compute_crs_hardcoded(inp)
            result.breakdown["calculation_method"] = "hardcoded_fallback"
            result.breakdown["rule_check_note"] = "Rule check uncertain, using hardcoded for determinism"
            return result
    
    # Rules changed or don't match - use AI (with temperature=0 for determinism)
    logger.warning(f"CRS calculation: Using AI method (rules changed: {rule_check.changes_detected})")
    try:
        result = compute_crs_with_ai(inp, rule_check.official_rules_summary)
        result.breakdown["calculation_method"] = "ai_based"
        result.breakdown["rule_changes"] = rule_check.changes_detected
        result.breakdown["rule_check_timestamp"] = rule_check.last_checked.isoformat()
        logger.info(f"CRS calculation: AI method completed, total={result.total}")
        return result
    except Exception as e:
        # If AI fails, fallback to hardcoded with warning
        logger.error(f"CRS AI calculation failed: {e}, falling back to hardcoded")
        result = compute_crs_hardcoded(inp)
        result.breakdown["calculation_method"] = "hardcoded_fallback"
        result.breakdown["ai_calculation_error"] = str(e)
        result.breakdown["rule_changes_detected"] = rule_check.changes_detected
        result.missing_or_defaulted.append("ai_calculation_failed")
        return result


def get_rule_check_status() -> dict[str, Any]:
    """Get current rule check status (for debugging/monitoring)."""
    try:
        rule_check = _get_rule_check()
        return {
            "rules_match": rule_check.rules_match,
            "use_hardcoded": rule_check.use_hardcoded,
            "changes_detected": rule_check.changes_detected,
            "last_checked": rule_check.last_checked.isoformat() if rule_check.last_checked else None,
            "error": rule_check.error,
            "cache_age_seconds": (
                (datetime.utcnow() - _cache_timestamp).total_seconds()
                if _cache_timestamp else None
            ),
        }
    except Exception as e:
        return {
            "error": str(e),
            "rules_match": None,
            "use_hardcoded": True,  # Default to hardcoded on error
        }


def clear_rule_check_cache() -> None:
    """Clear the rule check cache (force fresh check on next call)."""
    global _rule_check_cache, _cache_timestamp
    _rule_check_cache = None
    _cache_timestamp = None
