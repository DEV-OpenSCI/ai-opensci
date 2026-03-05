"""Semantic Scholar MCP Server — 学术论文搜索、引用关系、作者信息"""

import json
from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("scholar-server", instructions="Search academic papers via Semantic Scholar API")

BASE_URL = "https://api.semanticscholar.org/graph/v1"
FIELDS = "paperId,title,abstract,year,citationCount,authors,url,venue,publicationDate,externalIds"


@mcp.tool()
async def search_papers(query: str, limit: int = 10, year_from: int | None = None, year_to: int | None = None) -> str:
    """Search academic papers by keyword or research question.

    Args:
        query: Search query (keywords or research question)
        limit: Max number of results (1-100, default 10)
        year_from: Filter papers published from this year
        year_to: Filter papers published up to this year
    """
    params = {"query": query, "limit": min(limit, 100), "fields": FIELDS}
    if year_from or year_to:
        year_range = f"{year_from or ''}-{year_to or ''}"
        params["year"] = year_range

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{BASE_URL}/paper/search", params=params)
        resp.raise_for_status()
        data = resp.json()

    papers = data.get("data", [])
    if not papers:
        return "No papers found for this query."

    results = []
    for p in papers:
        authors = ", ".join(a.get("name", "") for a in (p.get("authors") or [])[:5])
        results.append(
            f"**{p.get('title', 'Untitled')}**\n"
            f"  Authors: {authors}\n"
            f"  Year: {p.get('year', 'N/A')} | Citations: {p.get('citationCount', 0)}\n"
            f"  Venue: {p.get('venue', 'N/A')}\n"
            f"  Abstract: {(p.get('abstract') or 'N/A')[:300]}\n"
            f"  URL: {p.get('url', 'N/A')}\n"
            f"  Paper ID: {p.get('paperId', '')}"
        )
    return "\n\n---\n\n".join(results)


@mcp.tool()
async def get_paper_details(paper_id: str) -> str:
    """Get detailed information for a specific paper.

    Args:
        paper_id: Semantic Scholar paper ID, DOI, or ArXiv ID (e.g. 'DOI:10.1234/xxx' or 'ArXiv:2301.00001')
    """
    fields = f"{FIELDS},references,citations,tldr"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{BASE_URL}/paper/{paper_id}", params={"fields": fields})
        resp.raise_for_status()
        p = resp.json()

    authors = ", ".join(a.get("name", "") for a in (p.get("authors") or []))
    tldr = p.get("tldr", {}).get("text", "N/A") if p.get("tldr") else "N/A"
    refs = len(p.get("references") or [])
    cites = len(p.get("citations") or [])

    return (
        f"**{p.get('title', 'Untitled')}**\n\n"
        f"Authors: {authors}\n"
        f"Year: {p.get('year', 'N/A')} | Venue: {p.get('venue', 'N/A')}\n"
        f"Citations: {p.get('citationCount', 0)} | References in paper: {refs} | Cited by (fetched): {cites}\n"
        f"TL;DR: {tldr}\n\n"
        f"Abstract:\n{p.get('abstract', 'N/A')}\n\n"
        f"URL: {p.get('url', 'N/A')}"
    )


@mcp.tool()
async def get_citations(paper_id: str, limit: int = 20) -> str:
    """Get papers that cite a given paper (forward citations).

    Args:
        paper_id: Semantic Scholar paper ID
        limit: Max number of citations to return
    """
    fields = "paperId,title,year,citationCount,authors,venue"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{BASE_URL}/paper/{paper_id}/citations",
            params={"fields": fields, "limit": min(limit, 100)},
        )
        resp.raise_for_status()
        data = resp.json()

    citations = data.get("data", [])
    if not citations:
        return "No citations found."

    results = []
    for item in citations:
        p = item.get("citingPaper", {})
        authors = ", ".join(a.get("name", "") for a in (p.get("authors") or [])[:3])
        results.append(
            f"- **{p.get('title', 'Untitled')}** ({p.get('year', '?')}) "
            f"by {authors} | Cited: {p.get('citationCount', 0)} | {p.get('venue', '')}"
        )
    return f"**Citations ({len(results)}):**\n\n" + "\n".join(results)


@mcp.tool()
async def get_references(paper_id: str, limit: int = 20) -> str:
    """Get papers referenced by a given paper (backward citations).

    Args:
        paper_id: Semantic Scholar paper ID
        limit: Max number of references to return
    """
    fields = "paperId,title,year,citationCount,authors,venue"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{BASE_URL}/paper/{paper_id}/references",
            params={"fields": fields, "limit": min(limit, 100)},
        )
        resp.raise_for_status()
        data = resp.json()

    refs = data.get("data", [])
    if not refs:
        return "No references found."

    results = []
    for item in refs:
        p = item.get("citedPaper", {})
        authors = ", ".join(a.get("name", "") for a in (p.get("authors") or [])[:3])
        results.append(
            f"- **{p.get('title', 'Untitled')}** ({p.get('year', '?')}) "
            f"by {authors} | Cited: {p.get('citationCount', 0)} | {p.get('venue', '')}"
        )
    return f"**References ({len(results)}):**\n\n" + "\n".join(results)


@mcp.tool()
async def search_author(name: str) -> str:
    """Search for an author and get their profile with top papers.

    Args:
        name: Author name to search
    """
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{BASE_URL}/author/search",
            params={"query": name, "fields": "authorId,name,hIndex,citationCount,paperCount", "limit": 5},
        )
        resp.raise_for_status()
        data = resp.json()

    authors = data.get("data", [])
    if not authors:
        return "No authors found."

    results = []
    for a in authors:
        results.append(
            f"**{a.get('name', 'Unknown')}**\n"
            f"  h-index: {a.get('hIndex', 'N/A')} | Papers: {a.get('paperCount', 0)} | Citations: {a.get('citationCount', 0)}\n"
            f"  Author ID: {a.get('authorId', '')}"
        )
    return "\n\n".join(results)


if __name__ == "__main__":
    mcp.run()
