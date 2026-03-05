"""Consensus MCP Server — 用问句搜索学术论文，返回 AI 提炼的支持/反对结论"""

import os
from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("consensus-server", instructions="Search academic papers with research questions via Consensus, returns AI-generated takeaways")

BASE_URL = "https://api.consensus.app"
API_KEY = os.environ.get("CONSENSUS_API_KEY", "")


def _headers():
    if not API_KEY:
        raise RuntimeError("CONSENSUS_API_KEY environment variable is not set. Apply at https://consensus.app/home/api/")
    return {"x-api-key": API_KEY}


@mcp.tool()
async def search_papers(
    query: str,
    year_min: int | None = None,
    year_max: int | None = None,
    study_types: list[str] | None = None,
    human_only: bool = False,
    exclude_preprints: bool = False,
    medical_mode: bool = False,
) -> str:
    """Search academic papers using a research question. Returns top 20 papers with AI-generated takeaways.

    Args:
        query: Research question in natural language (e.g. "Does creatine improve muscle strength?")
        year_min: Only include papers from this year onwards
        year_max: Only include papers up to this year
        study_types: Filter by type: "rct", "meta-analysis", "systematic review", "literature review", "non-rct observational study", "non-rct experimental", "case report", "animal", "non-rct in vitro"
        human_only: Only include human studies
        exclude_preprints: Only include peer-reviewed papers
        medical_mode: Filter to top medical journals (~8M docs)
    """
    params: dict = {"query": query}
    if year_min:
        params["year_min"] = year_min
    if year_max:
        params["year_max"] = year_max
    if human_only:
        params["human"] = True
    if exclude_preprints:
        params["exclude_preprints"] = True
    if medical_mode:
        params["medical_mode"] = True

    # study_types is a repeated query param
    query_string = ""
    if study_types:
        for st in study_types:
            query_string += f"&study_types={st}"

    async with httpx.AsyncClient(timeout=30) as client:
        url = f"{BASE_URL}/v1/quick_search"
        resp = await client.get(url + ("?" + "&".join(f"{k}={v}" for k, v in params.items()) + query_string if query_string else ""),
                                headers=_headers(),
                                params=params if not query_string else None)
        resp.raise_for_status()
        data = resp.json()

    papers = data.get("results", [])
    if not papers:
        return "No papers found on Consensus for this query."

    results = []
    for p in papers:
        authors = ", ".join(p.get("authors", [])[:5])
        takeaway = p.get("takeaway", "N/A")
        study_type = p.get("study_type", "")
        type_badge = f" [{study_type}]" if study_type else ""

        results.append(
            f"**{p.get('title', 'Untitled')}**{type_badge}\n"
            f"  Authors: {authors}\n"
            f"  Year: {p.get('publish_year', 'N/A')} | Citations: {p.get('citation_count', 0)}\n"
            f"  Journal: {p.get('journal_name', 'N/A')}\n"
            f"  DOI: {p.get('doi', 'N/A')}\n"
            f"  **Takeaway: {takeaway}**\n"
            f"  URL: {p.get('url', 'N/A')}"
        )
    return f"**Consensus Search Results ({len(results)} papers):**\n\n" + "\n\n---\n\n".join(results)


if __name__ == "__main__":
    mcp.run()
