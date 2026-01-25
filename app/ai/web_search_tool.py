"""
Web search tool for the immigration consultant chat agent.

Uses Tavily (TAVILY_API_KEY) when set; otherwise DuckDuckGo (no API key).
DuckDuckGo often rate-limits or blocks requests, so Tavily is more reliable
for CRS cutoffs, Express Entry draw dates, and immigration news.
"""

from __future__ import annotations

import os
import time

from crewai.tools import tool


SEARCH_UNAVAILABLE_MSG = (
    "Web search is temporarily unavailable (rate limit or network error). "
    "Answer using general knowledge. Recommend IRCC, official sources, or "
    "trusted immigration news for current CRS cutoffs and draw dates."
)


def _normalize(r: dict) -> dict:
    """Normalize search result to {title, body, href}."""
    title = (r.get("title") or "").strip()
    body = (r.get("body") or r.get("content") or "").strip()
    href = (r.get("href") or r.get("url") or "").strip()
    return {"title": title, "body": body, "href": href}


def _run_tavily(query: str, max_results: int = 8) -> list[dict] | None:
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from tavily import TavilyClient
    except ImportError:
        return None
    try:
        client = TavilyClient(api_key=api_key)
        resp = client.search(
            query,
            max_results=max_results,
            search_depth="basic",
            days=180,
        )
        raw = (resp or {}).get("results") or []
        return [_normalize(r) for r in raw]
    except Exception:
        return None


def _run_duckduckgo(query: str, max_results: int = 8) -> list[dict] | None:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return None
    delay = 1.5
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            if attempt > 0:
                time.sleep(delay * (attempt + 1))
            else:
                time.sleep(0.8)
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            return [_normalize(r) for r in (results or [])]
        except Exception:
            if attempt == max_attempts - 1:
                return None
    return None


def _run_search(query: str, max_results: int = 8) -> list[dict] | None:
    """Run search via Tavily (if key set) or DuckDuckGo. Returns None on failure."""
    normalized = _run_tavily(query, max_results)
    if normalized is not None:
        return normalized
    return _run_duckduckgo(query, max_results)


def _format_results(results: list[dict]) -> str:
    if not results:
        return "No search results found."
    lines = []
    for i, r in enumerate(results, 1):
        title = (r.get("title") or "").strip()
        body = (r.get("body") or "").strip()
        href = (r.get("href") or "").strip()
        if title or body:
            lines.append(f"{i}. **{title}**\n   {body}\n   Source: {href}")
    return "\n\n".join(lines) if lines else "No search results found."


@tool("Web search for immigration and CRS info")
def web_search_immigration(query: str) -> str:
    """
    Search the web for current Canadian immigration info. Use when the user asks
    about: recent CRS cutoffs, Express Entry draw dates, next draw, Canadian
    immigration news, IRCC updates, PNP streams, proof of funds, ECA, etc.

    Always include the CURRENT YEAR (e.g. 2026) or "latest" in the query for
    cutoffs/draws (e.g. "Express Entry CRS cutoffs 2026", "IRCC draw January 2026",
    "latest Express Entry draw 2026"). "Recent" = last 1–6 months only.
    Returns titles, snippets, and URLs.
    """
    results = _run_search(query, max_results=8)
    if results is None:
        return SEARCH_UNAVAILABLE_MSG
    return _format_results(results)
