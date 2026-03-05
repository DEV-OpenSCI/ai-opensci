"""CrossRef MCP Server — DOI解析、期刊信息、引用计数"""

import os
from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("crossref-server", instructions="Resolve DOIs and get journal/citation metadata via CrossRef")

BASE_URL = "https://api.crossref.org"
_mailto = os.environ.get("CROSSREF_MAILTO", "")
HEADERS = {"User-Agent": f"ai-opensci/0.1 (mailto:{_mailto})"} if _mailto else {"User-Agent": "ai-opensci/0.1"}


@mcp.tool()
async def resolve_doi(doi: str) -> str:
    """Resolve a DOI and get detailed publication metadata.

    Args:
        doi: DOI string (e.g. '10.1038/s41586-023-06600-9')
    """
    doi = doi.strip().removeprefix("https://doi.org/").removeprefix("http://doi.org/")

    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        try:
            resp = await client.get(f"{BASE_URL}/works/{doi}")
            if resp.status_code == 404:
                return f"DOI not found: {doi}"
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            return f"CrossRef API error: {e.response.status_code} — {e.response.text[:200]}"
        except httpx.RequestError as e:
            return f"CrossRef API request failed: {e}"
        item = resp.json().get("message", {})

    title = " ".join(item.get("title", ["Untitled"]))
    authors = []
    for a in item.get("author", []):
        name = f"{a.get('given', '')} {a.get('family', '')}".strip()
        if name:
            authors.append(name)

    journal = " ".join(item.get("container-title", ["N/A"]))
    pub_date = item.get("published", {}).get("date-parts", [[]])[0]
    date_str = "-".join(str(d) for d in pub_date) if pub_date else "N/A"
    cited = item.get("is-referenced-by-count", 0)
    ref_count = item.get("references-count", 0)
    publisher = item.get("publisher", "N/A")
    doc_type = item.get("type", "N/A")
    issn = ", ".join(item.get("ISSN", []))
    license_info = ""
    if item.get("license"):
        license_info = item["license"][0].get("URL", "")

    return (
        f"**{title}**\n\n"
        f"DOI: {doi}\n"
        f"Authors: {', '.join(authors)}\n"
        f"Journal: {journal}\n"
        f"Publisher: {publisher}\n"
        f"Published: {date_str}\n"
        f"Type: {doc_type}\n"
        f"Cited by: {cited} | References: {ref_count}\n"
        f"ISSN: {issn or 'N/A'}\n"
        f"License: {license_info or 'N/A'}"
    )


@mcp.tool()
async def search_crossref(query: str, limit: int = 10, filter_type: str | None = None) -> str:
    """Search CrossRef for publications.

    Args:
        query: Search query
        limit: Max results (1-50)
        filter_type: Filter by type — 'journal-article', 'proceedings-article', 'book-chapter', etc.
    """
    params = {"query": query, "rows": min(limit, 50)}
    if filter_type:
        params["filter"] = f"type:{filter_type}"

    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        try:
            resp = await client.get(f"{BASE_URL}/works", params=params)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            return f"CrossRef API error: {e.response.status_code} — {e.response.text[:200]}"
        except httpx.RequestError as e:
            return f"CrossRef API request failed: {e}"
        items = resp.json().get("message", {}).get("items", [])

    if not items:
        return "No results found on CrossRef."

    results = []
    for item in items:
        title = " ".join(item.get("title", ["Untitled"]))
        authors = []
        for a in item.get("author", [])[:3]:
            name = f"{a.get('given', '')} {a.get('family', '')}".strip()
            if name:
                authors.append(name)
        journal = " ".join(item.get("container-title", [""]))
        pub_date = item.get("published", {}).get("date-parts", [[]])[0]
        year = pub_date[0] if pub_date else "N/A"
        cited = item.get("is-referenced-by-count", 0)
        doi = item.get("DOI", "")

        results.append(
            f"**{title}**\n"
            f"  {', '.join(authors)} | {journal} ({year})\n"
            f"  Cited by: {cited} | DOI: {doi}"
        )
    return "\n\n".join(results)


@mcp.tool()
async def get_journal_info(issn: str) -> str:
    """Get journal information by ISSN.

    Args:
        issn: Journal ISSN (e.g. '0028-0836' for Nature)
    """
    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        try:
            resp = await client.get(f"{BASE_URL}/journals/{issn}")
            if resp.status_code == 404:
                return f"Journal not found with ISSN: {issn}"
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            return f"CrossRef API error: {e.response.status_code} — {e.response.text[:200]}"
        except httpx.RequestError as e:
            return f"CrossRef API request failed: {e}"
        j = resp.json().get("message", {})

    title = j.get("title", "N/A")
    publisher = j.get("publisher", "N/A")
    subjects = ", ".join(s.get("name", "") for s in j.get("subjects", []))
    issn_list = ", ".join(j.get("ISSN", []))
    total_dois = j.get("counts", {}).get("total-dois", 0)

    # Coverage info
    coverage = j.get("coverage", {})
    abstract_cov = coverage.get("abstracts-current", 0)
    ref_cov = coverage.get("references-current", 0)

    return (
        f"**{title}**\n\n"
        f"Publisher: {publisher}\n"
        f"ISSN: {issn_list}\n"
        f"Subjects: {subjects or 'N/A'}\n"
        f"Total DOIs: {total_dois}\n"
        f"Abstract coverage: {abstract_cov:.0%}\n"
        f"Reference coverage: {ref_cov:.0%}"
    )


if __name__ == "__main__":
    mcp.run()
