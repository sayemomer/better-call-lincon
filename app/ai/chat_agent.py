"""
Immigration consultant chat agent using CrewAI.

The agent has access to the user's profile, uploaded documents metadata,
and CRS score (if computable). It uses a web search tool to look up current
CRS cutoffs, draw dates, and immigration news when relevant.

Not legal advice. For general guidance only.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from crewai import Agent, Task, Crew, Process, LLM

from app.ai.web_search_tool import web_search_immigration


def _build_profile_context(profile_data: dict[str, Any] | None) -> str:
    if not profile_data:
        return "No profile data available. The user has not completed their profile or uploaded documents yet."
    # Flatten for readability; avoid huge dumps
    safe = {k: v for k, v in profile_data.items() if v is not None}
    return json.dumps(safe, indent=2, default=str)


def _build_documents_context(documents: list[dict[str, Any]]) -> str:
    if not documents:
        return "No documents uploaded yet."
    lines = []
    for d in documents:
        name = d.get("filename") or d.get("storage_url") or "unknown"
        t = d.get("type_detected") or "unknown"
        lines.append(f"- {name} (type: {t})")
    return "\n".join(lines)


def _build_crs_context(crs_result: dict[str, Any] | None) -> str:
    if not crs_result:
        return "CRS score has not been computed (e.g. missing profile data)."
    total = crs_result.get("total", 0)
    breakdown = crs_result.get("breakdown") or {}
    missing = crs_result.get("missing_or_defaulted") or []
    disclaim = crs_result.get("disclaimer") or ""
    lines = [
        f"Total CRS: {total}",
        f"Breakdown: {json.dumps(breakdown, default=str)}",
    ]
    if missing:
        lines.append(f"Missing or defaulted fields: {', '.join(missing)}")
    if disclaim:
        lines.append(f"Note: {disclaim}")
    return "\n".join(lines)


def _build_history_context(history: list[dict[str, str]] | None) -> str:
    if not history:
        return ""
    lines = ["### Prior conversation\n"]
    for h in history:
        role = (h.get("role") or "user").lower()
        content = (h.get("content") or "").strip()
        if not content:
            continue
        label = "User" if role == "user" else "Consultant"
        lines.append(f"**{label}:** {content}\n")
    return "\n".join(lines)


def run_immigration_chat(
    profile_context: str,
    documents_context: str,
    crs_context: str,
    user_message: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    """
    Run the immigration consultant CrewAI agent and return the reply.

    Context (profile, documents, CRS) is injected. The agent uses the web search
    tool to look up current CRS cutoffs, draw dates, and immigration news when
    the user asks (e.g. "When is the next draw?", "What are recent CRS cutoffs?").
    """
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required for the chat agent.")

    model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
    llm = LLM(model=model, api_key=openrouter_api_key, base_url="https://openrouter.ai/api/v1")

    agent = Agent(
        role="Immigration Consultant",
        goal=(
            "Help users with Canadian immigration: CRS scores, Express Entry, CEC/FSW eligibility, "
            "PNP, timelines, permit status/expiry, and pathways. Use their profile, documents, "
            "and CRS data when relevant. Use the web search tool to fetch current CRS cutoffs, "
            "draw dates, and immigration news when the user asks."
        ),
        backstory=(
            "You are an experienced Canadian immigration consultant. You have access to the user's "
            "profile, uploaded documents (types and filenames), and their CRS score when available. "
            "You also have a web search tool: use it to look up current Express Entry CRS cutoffs, "
            "when the next draw is, and recent draw results. 'Recent' means the last 1–6 months only. "
            "Always include the current year in search queries (e.g. 2026). Never cite cutoffs or "
            "draws older than 6 months as 'recent'. Answer clearly and practically. Suggest pathways "
            "(e.g. PNP, French, CEC) when relevant. You never give legal advice; recommend consulting "
            "an authorized representative or IRCC. You are helpful, concise, and accurate."
        ),
        tools=[web_search_immigration],
        llm=llm,
        verbose=False,
    )

    history_block = _build_history_context(history)
    history_section = f"\n{history_block}\n" if history_block else ""

    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    current_year = str(now.year)

    task_desc = f"""You are an immigration consultant chatting with a user. Use the context below.

## Today's date
{today_str}. "Recent" means the last 1–2 months, or at most 6 months from today. Do NOT use or cite data older than 6 months as "recent" CRS cutoffs or draw dates.

## User profile (from their account)
{profile_context}

## Uploaded documents (in system uploads folder)
{documents_context}

## User's CRS score (if computed)
{crs_context}
{history_section}

## User's current message
{user_message}

Instructions:
- Use their profile, documents, and CRS when relevant to answer.
- When the user asks about recent CRS cutoffs, next draw, draw dates, or immigration news, USE THE WEB SEARCH TOOL. Always include the CURRENT YEAR ({current_year}) or "latest" in your search query (e.g. "Express Entry CRS cutoffs {current_year}", "IRCC Express Entry draw January {current_year}", "latest Express Entry draw {current_year}"). Do not guess; search for current info.
- If search results only contain old data (e.g. 2023 or older), do NOT present it as recent. Say you found only older data and recommend IRCC or official sources for the latest. Never cite cutoffs from more than 6 months ago as "recent".
- Be clear, practical, and cite sources when you use search results.
- Suggest pathways (PNP, French, CEC) when useful.
- Do not output JSON or code blocks.
- Add a brief disclaimer that this is general guidance only and not legal advice."""

    task = Task(
        description=task_desc,
        expected_output="A clear, helpful plain-text reply to the user's immigration question.",
        agent=agent,
    )

    crew = Crew(process=Process.sequential, agents=[agent], tasks=[task])
    result = crew.kickoff()
    raw = result.raw if hasattr(result, "raw") else str(result)
    return (raw or "").strip()
