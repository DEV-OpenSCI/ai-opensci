"""Paper Store MCP Server — 文献本地存储管理，下载 PDF + 保存元数据 JSON"""

import json
import os
import re
import hashlib
from datetime import datetime
from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("paper-store", instructions="Download and manage academic papers locally (PDF + metadata JSON)")

# Default store path, can be overridden via env
STORE_DIR = os.environ.get("PAPER_STORE_DIR", os.path.expanduser("~/ai-opensci-papers"))


def _ensure_store():
    os.makedirs(STORE_DIR, exist_ok=True)
    os.makedirs(os.path.join(STORE_DIR, "pdfs"), exist_ok=True)
    os.makedirs(os.path.join(STORE_DIR, "metadata"), exist_ok=True)


def _safe_filename(title: str) -> str:
    """Generate a filesystem-safe filename from paper title."""
    clean = re.sub(r"[^\w\s-]", "", title)
    clean = re.sub(r"\s+", "_", clean.strip())
    return clean[:80]


def _paper_id(doi: str = "", title: str = "") -> str:
    """Generate a unique ID for a paper."""
    key = doi if doi else title
    return hashlib.sha256(key.encode()).hexdigest()[:12]


def _load_index() -> dict:
    """Load the papers index."""
    index_path = os.path.join(STORE_DIR, "index.json")
    if os.path.exists(index_path):
        with open(index_path) as f:
            return json.load(f)
    return {"papers": {}, "updated_at": None}


def _save_index(index: dict):
    index["updated_at"] = datetime.now().isoformat()
    index_path = os.path.join(STORE_DIR, "index.json")
    with open(index_path, "w") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


@mcp.tool()
async def save_paper(
    title: str,
    authors: str = "",
    year: int | None = None,
    abstract: str = "",
    doi: str = "",
    url: str = "",
    venue: str = "",
    citations: int = 0,
    source: str = "",
    takeaway: str = "",
    pdf_url: str = "",
) -> str:
    """Save a paper's metadata and optionally download its PDF.

    Args:
        title: Paper title (required)
        authors: Comma-separated author names
        year: Publication year
        abstract: Paper abstract
        doi: DOI identifier
        url: Paper URL (landing page)
        venue: Journal or conference name
        citations: Citation count
        source: Where this paper was found (e.g. "Semantic Scholar", "Elicit", "Consensus")
        takeaway: AI-generated key takeaway (from Consensus)
        pdf_url: Direct PDF download URL (if available)
    """
    _ensure_store()
    pid = _paper_id(doi, title)
    safe_name = _safe_filename(title)

    # Save metadata
    metadata = {
        "id": pid,
        "title": title,
        "authors": authors,
        "year": year,
        "abstract": abstract,
        "doi": doi,
        "url": url,
        "venue": venue,
        "citations": citations,
        "source": source,
        "takeaway": takeaway,
        "pdf_url": pdf_url,
        "pdf_path": None,
        "saved_at": datetime.now().isoformat(),
    }

    # Try downloading PDF
    pdf_path = None
    if pdf_url:
        try:
            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
                resp = await client.get(pdf_url)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    pdf_filename = f"{safe_name}_{pid}.pdf"
                    pdf_path = os.path.join(STORE_DIR, "pdfs", pdf_filename)
                    with open(pdf_path, "wb") as f:
                        f.write(resp.content)
                    metadata["pdf_path"] = pdf_path
        except Exception as e:
            metadata["pdf_download_error"] = str(e)

    # If no direct PDF URL, try Semantic Scholar / arXiv PDF
    if not pdf_path and doi:
        for attempt_url in [
            f"https://arxiv.org/pdf/{doi}" if "arxiv" in doi.lower() else None,
        ]:
            if not attempt_url:
                continue
            try:
                async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
                    resp = await client.get(attempt_url)
                    if resp.status_code == 200 and len(resp.content) > 1000:
                        pdf_filename = f"{safe_name}_{pid}.pdf"
                        pdf_path = os.path.join(STORE_DIR, "pdfs", pdf_filename)
                        with open(pdf_path, "wb") as f:
                            f.write(resp.content)
                        metadata["pdf_path"] = pdf_path
                        break
            except Exception:
                pass

    # Save metadata JSON
    meta_path = os.path.join(STORE_DIR, "metadata", f"{safe_name}_{pid}.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    # Update index
    index = _load_index()
    index["papers"][pid] = {
        "title": title,
        "year": year,
        "doi": doi,
        "source": source,
        "has_pdf": pdf_path is not None,
        "meta_path": meta_path,
        "pdf_path": pdf_path,
    }
    _save_index(index)

    status = f"✅ Saved: **{title}**\n"
    status += f"  Metadata: {meta_path}\n"
    if pdf_path:
        status += f"  PDF: {pdf_path}\n"
    else:
        status += f"  PDF: not downloaded (no direct URL available)\n"
    return status


@mcp.tool()
async def save_papers_batch(papers_json: str) -> str:
    """Save multiple papers at once. Pass a JSON array of paper objects.

    Args:
        papers_json: JSON array string, each item has: title, authors, year, abstract, doi, url, venue, citations, source, takeaway, pdf_url
    """
    try:
        papers = json.loads(papers_json)
    except json.JSONDecodeError:
        return "Error: Invalid JSON input"

    results = []
    for p in papers:
        result = await save_paper(
            title=p.get("title", "Untitled"),
            authors=p.get("authors", ""),
            year=p.get("year"),
            abstract=p.get("abstract", ""),
            doi=p.get("doi", ""),
            url=p.get("url", ""),
            venue=p.get("venue", ""),
            citations=p.get("citations", 0),
            source=p.get("source", ""),
            takeaway=p.get("takeaway", ""),
            pdf_url=p.get("pdf_url", ""),
        )
        results.append(result)
    return "\n".join(results)


@mcp.tool()
async def list_papers() -> str:
    """List all saved papers in the local store."""
    _ensure_store()
    index = _load_index()
    papers = index.get("papers", {})

    if not papers:
        return f"No papers saved yet. Store location: {STORE_DIR}"

    lines = [f"**Paper Store** ({len(papers)} papers) — `{STORE_DIR}`\n"]
    lines.append("| # | Title | Year | Source | PDF |")
    lines.append("|---|-------|------|--------|-----|")

    for i, (pid, p) in enumerate(papers.items(), 1):
        pdf_mark = "✅" if p.get("has_pdf") else "❌"
        lines.append(f"| {i} | {p['title'][:60]} | {p.get('year', '?')} | {p.get('source', '')} | {pdf_mark} |")

    return "\n".join(lines)


@mcp.tool()
async def get_paper(query: str) -> str:
    """Get full metadata for a saved paper by title keyword or DOI.

    Args:
        query: Title keyword or DOI to search for
    """
    _ensure_store()
    index = _load_index()
    query_lower = query.lower()

    for pid, p in index.get("papers", {}).items():
        if query_lower in p.get("title", "").lower() or query_lower in p.get("doi", "").lower():
            meta_path = p.get("meta_path", "")
            if meta_path and os.path.exists(meta_path):
                with open(meta_path) as f:
                    metadata = json.load(f)
                return json.dumps(metadata, ensure_ascii=False, indent=2)

    return f"No paper found matching: {query}"


@mcp.tool()
async def export_references(format: str = "markdown") -> str:
    """Export all saved papers as a formatted reference list.

    Args:
        format: Output format — "markdown" (default) or "bibtex"
    """
    _ensure_store()
    index = _load_index()
    papers = index.get("papers", {})

    if not papers:
        return "No papers to export."

    if format == "bibtex":
        entries = []
        for pid, p in papers.items():
            meta_path = p.get("meta_path", "")
            if not meta_path or not os.path.exists(meta_path):
                continue
            with open(meta_path) as f:
                m = json.load(f)
            authors_bib = m.get("authors", "Unknown").replace(", ", " and ")
            cite_key = f"{m.get('authors', 'unknown').split(',')[0].strip().split()[-1].lower()}{m.get('year', '0000')}"
            entry = (
                f"@article{{{cite_key}_{pid},\n"
                f"  title = {{{m.get('title', '')}}},\n"
                f"  author = {{{authors_bib}}},\n"
                f"  year = {{{m.get('year', '')}}},\n"
                f"  journal = {{{m.get('venue', '')}}},\n"
                f"  doi = {{{m.get('doi', '')}}},\n"
                f"}}\n"
            )
            entries.append(entry)
        return "\n".join(entries)

    # Markdown format
    lines = ["# References\n"]
    for i, (pid, p) in enumerate(papers.items(), 1):
        meta_path = p.get("meta_path", "")
        if not meta_path or not os.path.exists(meta_path):
            continue
        with open(meta_path) as f:
            m = json.load(f)
        doi_link = f"https://doi.org/{m['doi']}" if m.get("doi") else m.get("url", "")
        lines.append(
            f"{i}. {m.get('authors', 'Unknown')}. "
            f"**{m.get('title', 'Untitled')}**. "
            f"*{m.get('venue', '')}*, {m.get('year', '')}. "
            f"[{m.get('doi', 'link')}]({doi_link})"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
