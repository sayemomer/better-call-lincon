"""
Web search tool for the immigration consultant chat agent.

Uses DuckDuckGo (no API key). The agent calls this to look up current
CRS cutoffs, Express Entry draw dates, Canadian immigration news, etc.
"""

from __future__ import annotations

from crewai.tools import tool


def _run_search(query: str, max_results: int = 8) -> list[dict]:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        raise RuntimeError(
            "duckduckgo-search is required for web search. Install with: pip install duckduckgo-search"
        )
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return results or []
    except Exception as e:
        return [{"title": "Search error", "body": str(e), "href": ""}]


def _format_results(results: list[dict]) -> str:
    if not results:
        return "No search results found."
    lines = []
    for i, r in enumerate(results, 1):
        title = (r.get("title") or "").strip()
        body = (r.get("body") or "").strip()
        href = (r.get("href") or "").strip()
        lines.append(f"{i}. **{title}**\n   {body}\n   Source: {href}")
    return "\n\n".join(lines)


@tool("Web search for immigration and CRS info")
def web_search_immigration(query: str) -> str:
    """
    Search the web for current Canadian immigration info. Use this when the user
    asks about: recent CRS cutoffs, Express Entry draw dates, next draw, Canadian
            immigration news, IRCC updates, PNP streams, proof of funds, ECA, etc.

    Pass a clear search query (e.g. 'Express Entry CRS cutoffs 2025', 'IRCC next draw',
    'Canadian Experience Class latest draw'). Returns titles, snippets, and URLs.
    """
    results = _run_search(query, max_results=8)
    return _format_results(results)
