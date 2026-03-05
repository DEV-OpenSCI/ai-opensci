"""arXiv MCP Server — 预印本搜索、元数据获取、PDF下载链接"""

import re
import xml.etree.ElementTree as ET
from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("arxiv-server", instructions="Search and retrieve papers from arXiv")

ARXIV_API = "http://export.arxiv.org/api/query"
NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def _parse_entry(entry: ET.Element) -> dict:
    """Parse a single arXiv Atom entry."""
    title = (entry.findtext("atom:title", "", NS) or "").strip().replace("\n", " ")
    summary = (entry.findtext("atom:summary", "", NS) or "").strip().replace("\n", " ")
    published = entry.findtext("atom:published", "", NS)[:10]
    updated = entry.findtext("atom:updated", "", NS)[:10]

    authors = []
    for author in entry.findall("atom:author", NS):
        name = author.findtext("atom:name", "", NS)
        if name:
            authors.append(name)

    # Extract arXiv ID from entry id URL
    entry_id = entry.findtext("atom:id", "", NS)
    arxiv_id = entry_id.split("/abs/")[-1] if "/abs/" in entry_id else entry_id

    # Get PDF link
    pdf_link = ""
    for link in entry.findall("atom:link", NS):
        if link.get("title") == "pdf":
            pdf_link = link.get("href", "")

    # Categories
    categories = []
    for cat in entry.findall("arxiv:primary_category", NS):
        categories.append(cat.get("term", ""))
    for cat in entry.findall("atom:category", NS):
        term = cat.get("term", "")
        if term and term not in categories:
            categories.append(term)

    # DOI and journal ref
    doi = entry.findtext("arxiv:doi", "", NS) or ""
    journal_ref = entry.findtext("arxiv:journal_ref", "", NS) or ""

    return {
        "arxiv_id": arxiv_id,
        "title": title,
        "authors": authors,
        "summary": summary,
        "published": published,
        "updated": updated,
        "pdf_link": pdf_link,
        "categories": categories,
        "doi": doi,
        "journal_ref": journal_ref,
    }


@mcp.tool()
async def search_arxiv(
    query: str,
    limit: int = 10,
    sort_by: str = "relevance",
    category: str | None = None,
) -> str:
    """Search arXiv for preprints.

    Args:
        query: Search query (supports arXiv query syntax: ti:, au:, abs:, cat:)
        limit: Max results (1-50, default 10)
        sort_by: Sort order — 'relevance', 'lastUpdatedDate', or 'submittedDate'
        category: Filter by arXiv category (e.g. 'cs.AI', 'stat.ML', 'q-bio.BM')
    """
    search_query = query
    if category:
        search_query = f"cat:{category} AND ({query})"

    sort_map = {
        "relevance": "relevance",
        "lastUpdatedDate": "lastUpdatedDate",
        "submittedDate": "submittedDate",
    }

    params = {
        "search_query": f"all:{search_query}" if not any(p in query for p in ["ti:", "au:", "abs:", "cat:"]) else search_query,
        "start": 0,
        "max_results": min(limit, 50),
        "sortBy": sort_map.get(sort_by, "relevance"),
        "sortOrder": "descending",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(ARXIV_API, params=params)
        resp.raise_for_status()

    root = ET.fromstring(resp.text)
    entries = root.findall("atom:entry", NS)

    if not entries:
        return "No papers found on arXiv for this query."

    results = []
    for entry in entries:
        p = _parse_entry(entry)
        authors_str = ", ".join(p["authors"][:5])
        if len(p["authors"]) > 5:
            authors_str += f" et al. ({len(p['authors'])} authors)"
        cats = ", ".join(p["categories"][:3])
        results.append(
            f"**{p['title']}**\n"
            f"  arXiv: {p['arxiv_id']} | Published: {p['published']}\n"
            f"  Authors: {authors_str}\n"
            f"  Categories: {cats}\n"
            f"  Abstract: {p['summary'][:300]}...\n"
            f"  PDF: {p['pdf_link']}"
        )
    return "\n\n---\n\n".join(results)


@mcp.tool()
async def get_arxiv_paper(arxiv_id: str) -> str:
    """Get detailed metadata for a specific arXiv paper.

    Args:
        arxiv_id: arXiv paper ID (e.g. '2301.00001' or '2301.00001v2')
    """
    # Clean up the ID
    arxiv_id = re.sub(r"^(https?://)?arxiv\.org/(abs|pdf)/", "", arxiv_id)

    params = {"id_list": arxiv_id, "max_results": 1}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(ARXIV_API, params=params)
        resp.raise_for_status()

    root = ET.fromstring(resp.text)
    entries = root.findall("atom:entry", NS)

    if not entries:
        return f"Paper {arxiv_id} not found on arXiv."

    p = _parse_entry(entries[0])
    authors_str = ", ".join(p["authors"])
    cats = ", ".join(p["categories"])

    result = (
        f"**{p['title']}**\n\n"
        f"arXiv ID: {p['arxiv_id']}\n"
        f"Authors: {authors_str}\n"
        f"Published: {p['published']} | Updated: {p['updated']}\n"
        f"Categories: {cats}\n"
    )
    if p["doi"]:
        result += f"DOI: {p['doi']}\n"
    if p["journal_ref"]:
        result += f"Journal: {p['journal_ref']}\n"
    result += f"\nAbstract:\n{p['summary']}\n\nPDF: {p['pdf_link']}"
    return result


@mcp.tool()
async def get_arxiv_latex_source(arxiv_id: str) -> str:
    """Get the download URL for the LaTeX source of an arXiv paper.

    Args:
        arxiv_id: arXiv paper ID
    """
    arxiv_id = re.sub(r"^(https?://)?arxiv\.org/(abs|pdf)/", "", arxiv_id)
    source_url = f"https://arxiv.org/e-print/{arxiv_id}"
    return (
        f"LaTeX source download URL: {source_url}\n\n"
        f"To download, use: curl -L -o {arxiv_id.replace('/', '_')}.tar.gz {source_url}\n"
        f"Then extract: tar -xzf {arxiv_id.replace('/', '_')}.tar.gz"
    )


if __name__ == "__main__":
    mcp.run()
