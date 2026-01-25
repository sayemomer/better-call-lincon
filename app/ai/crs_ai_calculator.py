"""
AI-based CRS Calculator - Fallback when rules change.

Uses AI to calculate CRS scores based on current official rules when
hardcoded implementation doesn't match.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

try:
    from crewai import Agent, Task, Crew, Process, LLM
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False

from app.ai.crs_agent import CRSInput, CRSResult


def compute_crs_with_ai(inp: CRSInput, official_rules: dict[str, Any] | None = None) -> CRSResult:
    """
    Calculate CRS score using AI agent based on current official rules.
    
    This is used as a fallback when hardcoded rules don't match official rules.
    """
    if not CREWAI_AVAILABLE:
        raise RuntimeError("CrewAI not available. Cannot use AI-based CRS calculator.")
    
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY required for AI-based CRS calculation.")
    
    model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
    # Use temperature=0 and seed for deterministic results
    # Note: Some models may not support seed, but temperature=0 helps with determinism
    llm = LLM(
        model=model, 
        api_key=openrouter_api_key, 
        base_url="https://openrouter.ai/api/v1",
        temperature=0.0,  # Set to 0 for deterministic outputs
    )
    
    agent = Agent(
        role="CRS Score Calculator",
        goal="Calculate Express Entry CRS (Comprehensive Ranking System) score accurately based on current official IRCC rules.",
        backstory=(
            "You are an expert at calculating CRS scores for Canadian Express Entry. "
            "You use the official IRCC CRS criteria and calculator rules. "
            "You calculate points for: age, education, language (first and second official), "
            "Canadian work experience, foreign work experience, spouse factors, "
            "skill transferability, provincial nomination, Canadian study bonus, sibling, "
            "and certificate of qualification. You follow the official rules exactly."
        ),
        llm=llm,
        verbose=False,
    )
    
    # Convert CRSInput to dict for agent
    input_dict = {
        "age": inp.age,
        "marital_status": inp.marital_status,
        "spouse_accompanying": inp.spouse_accompanying,
        "spouse_canadian_pr": inp.spouse_canadian_pr,
        "education_level": inp.education_level,
        "education_level_detail": inp.education_level_detail,
        "canadian_education": inp.canadian_education,
        "language_test": inp.language_test,
        "lang_speaking": inp.lang_speaking,
        "lang_listening": inp.lang_listening,
        "lang_reading": inp.lang_reading,
        "lang_writing": inp.lang_writing,
        "has_second_language": inp.has_second_language,
        "second_lang_speaking": inp.second_lang_speaking,
        "second_lang_listening": inp.second_lang_listening,
        "second_lang_reading": inp.second_lang_reading,
        "second_lang_writing": inp.second_lang_writing,
        "canadian_work_years": inp.canadian_work_years,
        "foreign_work_years": inp.foreign_work_years,
        "certificate_of_qualification": inp.certificate_of_qualification,
        "provincial_nomination": inp.provincial_nomination,
        "sibling_in_canada": inp.sibling_in_canada,
        "spouse_education_level": inp.spouse_education_level,
        "spouse_canadian_work_years": inp.spouse_canadian_work_years,
        "spouse_language_test": inp.spouse_language_test,
        "spouse_lang_speaking": inp.spouse_lang_speaking,
        "spouse_lang_listening": inp.spouse_lang_listening,
        "spouse_lang_reading": inp.spouse_lang_reading,
        "spouse_lang_writing": inp.spouse_lang_writing,
    }
    
    rules_context = ""
    if official_rules:
        rules_context = f"\n\nCurrent official rules:\n{json.dumps(official_rules, indent=2)}\n"
    
    task = Task(
        description=(
            f"Calculate the Express Entry CRS score for this profile:\n{json.dumps(input_dict, indent=2)}\n\n"
            f"Use the official IRCC CRS criteria from:\n"
            f"https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/check-score.html\n\n"
            f"{rules_context}"
            f"Calculate points for:\n"
            f"1. Core human capital (age, education, language, Canadian work)\n"
            f"2. Spouse factors (if applicable)\n"
            f"3. Skill transferability (education+language, education+work, foreign work+language)\n"
            f"4. Additional points (provincial nomination, Canadian study, sibling, certificate, second language)\n\n"
            f"Output STRICT JSON ONLY:\n"
            '{\n'
            '  "total": number (0-1200),\n'
            '  "core_human_capital": number,\n'
            '  "spouse_factors": number,\n'
            '  "skill_transferability": number,\n'
            '  "additional_points": number,\n'
            '  "breakdown": {\n'
            '    "age": number,\n'
            '    "education": number,\n'
            '    "first_official_language": number,\n'
            '    "canadian_work_experience": number,\n'
            '    "spouse_factors": number,\n'
            '    "skill_transferability": number,\n'
            '    "provincial_nomination": number,\n'
            '    "canadian_study_bonus": number,\n'
            '    "sibling_in_canada": number,\n'
            '    "certificate_of_qualification": number,\n'
            '    "second_official_language": number\n'
            '  },\n'
            '  "missing_or_defaulted": ["list of missing fields"],\n'
            '  "calculation_method": "ai_based"\n'
            '}\n'
        ),
        expected_output="A strict JSON object with CRS score breakdown.",
        agent=agent,
    )
    
    crew = Crew(process=Process.sequential, agents=[agent], tasks=[task])
    result = crew.kickoff()
    
    raw = result.raw if hasattr(result, "raw") else str(result)
    
    # Parse JSON
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON from text
        import re
        json_match = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            raise ValueError(f"AI agent returned invalid JSON: {raw[:500]}")
    
    # Convert to CRSResult
    return CRSResult(
        total=data.get("total", 0),
        core_human_capital=data.get("core_human_capital", 0),
        spouse_factors=data.get("spouse_factors", 0),
        skill_transferability=data.get("skill_transferability", 0),
        additional_points=data.get("additional_points", 0),
        breakdown=data.get("breakdown", {}),
        missing_or_defaulted=data.get("missing_or_defaulted", []),
        disclaimer=(
            "This score was calculated using AI based on current official rules. "
            "Official IRCC system results govern. See Canada.ca Express Entry CRS calculator. Not legal advice."
        ),
    )
