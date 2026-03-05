"""Elicit MCP Server — AI 学术搜索，可输入研究问题自动找论文并提炼关键点"""

import os
from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("elicit-server", instructions="Search papers and generate research reports via Elicit API")

BASE_URL = "https://elicit.com"
API_KEY = os.environ.get("ELICIT_API_KEY", "")


def _headers():
    if not API_KEY:
        return {"Content-Type": "application/json"}
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def _check_api_key() -> str | None:
    """Return error message if API key is missing, None otherwise."""
    if not API_KEY:
        return "Error: ELICIT_API_KEY environment variable is not set. Get your key at https://elicit.com/settings"
    return None


@mcp.tool()
async def search_papers(
    query: str,
    max_results: int = 8,
    min_year: int | None = None,
    max_year: int | None = None,
    type_tags: list[str] | None = None,
    max_quartile: int | None = None,
) -> str:
    """Search 125M+ academic papers via Elicit. Supports natural language research questions.

    Args:
        query: Research question or keywords (natural language supported)
        max_results: Number of results (1-100, default 8)
        max_year: Only include papers published up to this year
        min_year: Only include papers from this year onwards
        type_tags: Filter by study type: "RCT", "Meta-Analysis", "Systematic Review", "Review", "Longitudinal"
        max_quartile: Journal quartile filter (1 = top 25% journals)
    """
    err = _check_api_key()
    if err:
        return err
    body: dict = {"query": query, "maxResults": min(max_results, 100)}
    filters: dict = {}
    if min_year:
        filters["minYear"] = min_year
    if max_year:
        filters["maxYear"] = max_year
    if type_tags:
        filters["typeTags"] = type_tags
    if max_quartile:
        filters["maxQuartile"] = max_quartile
    filters["retracted"] = "exclude_retracted"
    if filters:
        body["filters"] = filters

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(f"{BASE_URL}/api/v1/search", headers=_headers(), json=body)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            return f"Elicit API error: {e.response.status_code} — {e.response.text[:200]}"
        except httpx.RequestError as e:
            return f"Elicit API request failed: {e}"
        data = resp.json()

    papers = data.get("papers", [])
    if not papers:
        return "No papers found on Elicit for this query."

    results = []
    for p in papers:
        authors = ", ".join(p.get("authors", [])[:5])
        abstract = (p.get("abstract") or "N/A")[:300]
        urls = p.get("urls", [])
        url = urls[0] if urls else "N/A"
        results.append(
            f"**{p.get('title', 'Untitled')}**\n"
            f"  Authors: {authors}\n"
            f"  Year: {p.get('year', 'N/A')} | Citations: {p.get('citedByCount', 0)}\n"
            f"  Venue: {p.get('venue', 'N/A')}\n"
            f"  DOI: {p.get('doi', 'N/A')}\n"
            f"  Abstract: {abstract}\n"
            f"  URL: {url}"
        )
    return f"**Elicit Search Results ({len(results)} papers):**\n\n" + "\n\n---\n\n".join(results)


@mcp.tool()
async def create_report(
    research_question: str,
    max_search_papers: int = 50,
    max_extract_papers: int = 10,
) -> str:
    """Create an AI research report on Elicit (async, takes 5-15 min to complete).

    Args:
        research_question: The research question for the report
        max_search_papers: How many papers to search (1-5000, default 50)
        max_extract_papers: How many papers to extract data from (1-5000, default 10)
    """
    err = _check_api_key()
    if err:
        return err
    body = {
        "researchQuestion": research_question,
        "maxSearchPapers": max_search_papers,
        "maxExtractPapers": max_extract_papers,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(f"{BASE_URL}/api/v1/reports", headers=_headers(), json=body)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            return f"Elicit API error: {e.response.status_code} — {e.response.text[:200]}"
        except httpx.RequestError as e:
            return f"Elicit API request failed: {e}"
        data = resp.json()

    report_id = data.get("reportId", "")
    url = data.get("url", "")
    return (
        f"**Report created!**\n\n"
        f"Report ID: {report_id}\n"
        f"Status: {data.get('status', 'processing')}\n"
        f"URL: {url}\n\n"
        f"The report takes 5-15 minutes to generate. Use `get_report` with the report ID to check status."
    )


@mcp.tool()
async def get_report(report_id: str, include_body: bool = False) -> str:
    """Check the status of an Elicit research report and get results.

    Args:
        report_id: The report ID returned by create_report
        include_body: Whether to include the full report markdown body
    """
    err = _check_api_key()
    if err:
        return err
    params = {}
    if include_body:
        params["include"] = "reportBody"

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(f"{BASE_URL}/api/v1/reports/{report_id}", headers=_headers(), params=params)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            return f"Elicit API error: {e.response.status_code} — {e.response.text[:200]}"
        except httpx.RequestError as e:
            return f"Elicit API request failed: {e}"
        data = resp.json()

    status = data.get("status", "unknown")
    result = f"**Report Status: {status}**\n\n"
    result += f"URL: {data.get('url', 'N/A')}\n"

    if status == "completed":
        res = data.get("result", {})
        result += f"Title: {res.get('title', 'N/A')}\n"
        result += f"Summary: {res.get('summary', 'N/A')}\n"
        if data.get("pdfUrl"):
            result += f"PDF: {data['pdfUrl']}\n"
        if include_body and res.get("reportBody"):
            result += f"\n---\n\n{res['reportBody']}"
    elif status == "failed":
        err = data.get("error", {})
        result += f"Error: {err.get('message', 'Unknown error')}\n"

    return result


if __name__ == "__main__":
    mcp.run()
