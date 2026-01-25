#!/usr/bin/env python3
"""
Test script to verify CRS score determinism.

This script tests that the same input produces the same CRS score
across multiple calculations.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.ai.crs_agent import CRSInput, compute_crs as compute_crs_hardcoded
from app.ai.crs_dynamic import compute_crs as compute_crs_dynamic


def test_hardcoded_determinism():
    """Test that hardcoded calculation is deterministic."""
    print("=" * 60)
    print("Testing Hardcoded CRS Calculation Determinism")
    print("=" * 60)
    
    # Create a test input
    test_input = CRSInput(
        age=30,
        marital_status="single",
        spouse_accompanying=False,
        education_level="bachelors",
        education_level_detail="Bachelor's degree",
        canadian_education=False,
        language_test="ielts",
        lang_speaking=7.5,
        lang_listening=8.0,
        lang_reading=8.5,
        lang_writing=7.0,
        canadian_work_years=2,
        foreign_work_years=3,
        certificate_of_qualification=False,
        provincial_nomination=False,
        sibling_in_canada=False,
        has_second_language=False,
    )
    
    # Run calculation multiple times
    results = []
    num_runs = 10
    
    print(f"\nRunning hardcoded calculation {num_runs} times with same input...")
    for i in range(num_runs):
        result = compute_crs_hardcoded(test_input)
        results.append(result)
        print(f"Run {i+1}: Total = {result.total}, Method = {result.breakdown.get('calculation_method', 'hardcoded')}")
    
    # Check if all results are identical
    first_total = results[0].total
    all_same = all(r.total == first_total for r in results)
    
    if all_same:
        print(f"\n✅ PASS: All {num_runs} runs produced the same total score: {first_total}")
        print(f"   Breakdown: {results[0].breakdown}")
    else:
        print(f"\n❌ FAIL: Results are not deterministic!")
        totals = [r.total for r in results]
        print(f"   Scores: {totals}")
        print(f"   Unique scores: {set(totals)}")
        return False
    
    return True


def test_dynamic_determinism():
    """Test that dynamic calculation is deterministic (when forced to hardcoded)."""
    print("\n" + "=" * 60)
    print("Testing Dynamic CRS Calculation Determinism (forced hardcoded)")
    print("=" * 60)
    
    # Create a test input
    test_input = CRSInput(
        age=30,
        marital_status="single",
        spouse_accompanying=False,
        education_level="bachelors",
        education_level_detail="Bachelor's degree",
        canadian_education=False,
        language_test="ielts",
        lang_speaking=7.5,
        lang_listening=8.0,
        lang_reading=8.5,
        lang_writing=7.0,
        canadian_work_years=2,
        foreign_work_years=3,
        certificate_of_qualification=False,
        provincial_nomination=False,
        sibling_in_canada=False,
        has_second_language=False,
    )
    
    # Run calculation multiple times with force_hardcoded=True
    results = []
    num_runs = 10
    
    print(f"\nRunning dynamic calculation {num_runs} times with force_hardcoded=True...")
    for i in range(num_runs):
        result = compute_crs_dynamic(test_input, force_hardcoded=True)
        results.append(result)
        method = result.breakdown.get('calculation_method', 'unknown')
        print(f"Run {i+1}: Total = {result.total}, Method = {method}")
    
    # Check if all results are identical
    first_total = results[0].total
    all_same = all(r.total == first_total for r in results)
    all_hardcoded = all(r.breakdown.get('calculation_method') == 'hardcoded_forced' for r in results)
    
    if all_same and all_hardcoded:
        print(f"\n✅ PASS: All {num_runs} runs produced the same total score: {first_total}")
        print(f"   All used hardcoded method: {all_hardcoded}")
        print(f"   Breakdown: {results[0].breakdown}")
    else:
        print(f"\n❌ FAIL: Results are not deterministic!")
        totals = [r.total for r in results]
        methods = [r.breakdown.get('calculation_method') for r in results]
        print(f"   Scores: {totals}")
        print(f"   Methods: {methods}")
        print(f"   Unique scores: {set(totals)}")
        return False
    
    return True


def test_dynamic_default():
    """Test what method dynamic calculation uses by default."""
    print("\n" + "=" * 60)
    print("Testing Dynamic CRS Calculation (default behavior)")
    print("=" * 60)
    
    # Create a test input
    test_input = CRSInput(
        age=30,
        marital_status="single",
        spouse_accompanying=False,
        education_level="bachelors",
        education_level_detail="Bachelor's degree",
        canadian_education=False,
        language_test="ielts",
        lang_speaking=7.5,
        lang_listening=8.0,
        lang_reading=8.5,
        lang_writing=7.0,
        canadian_work_years=2,
        foreign_work_years=3,
        certificate_of_qualification=False,
        provincial_nomination=False,
        sibling_in_canada=False,
        has_second_language=False,
    )
    
    # Run calculation once to see what method is used
    print("\nRunning dynamic calculation (default behavior)...")
    result = compute_crs_dynamic(test_input)
    method = result.breakdown.get('calculation_method', 'unknown')
    
    print(f"Result: Total = {result.total}, Method = {method}")
    if 'rule_check' in result.breakdown:
        print(f"Rule check info: {result.breakdown.get('rule_check_warning', 'N/A')}")
    
    if method.startswith('hardcoded'):
        print("✅ Using hardcoded method (deterministic)")
        return True
    elif method == 'ai_based':
        print("⚠️  Using AI method (may not be deterministic)")
        print("   Recommendation: Use force_hardcoded=True for deterministic results")
        return False
    else:
        print(f"⚠️  Unknown method: {method}")
        return False


def main():
    """Run all determinism tests."""
    print("\n" + "=" * 60)
    print("CRS Score Determinism Test Suite")
    print("=" * 60)
    
    results = []
    
    # Test 1: Hardcoded determinism
    results.append(("Hardcoded Determinism", test_hardcoded_determinism()))
    
    # Test 2: Dynamic with force_hardcoded
    results.append(("Dynamic (forced hardcoded) Determinism", test_dynamic_determinism()))
    
    # Test 3: Dynamic default behavior
    results.append(("Dynamic Default Behavior", test_dynamic_default()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(passed for _, passed in results)
    
    if all_passed:
        print("\n✅ All determinism tests passed!")
    else:
        print("\n⚠️  Some tests failed. Review the output above.")
        print("\nRecommendation: Use force_hardcoded=True in API calls for deterministic results.")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
