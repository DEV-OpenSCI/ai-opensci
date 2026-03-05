"""PDF Reader MCP Server — 本地PDF论文解析，提取结构化内容"""

import os
import re
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("pdf-reader-server", instructions="Parse local PDF papers and extract structured text")


def _get_fitz():
    """Lazy import fitz (PyMuPDF)."""
    try:
        import fitz
        return fitz
    except ImportError:
        raise RuntimeError("PyMuPDF not installed. Run: pip install PyMuPDF")


@mcp.tool()
async def read_pdf(file_path: str, max_pages: int = 0) -> str:
    """Read a PDF file and extract its full text content.

    Args:
        file_path: Absolute path to the PDF file
        max_pages: Max pages to read (0 = all pages)
    """
    fitz = _get_fitz()
    file_path = os.path.expanduser(file_path)
    if not os.path.exists(file_path):
        return f"Error: File not found: {file_path}"

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        return f"Error: Failed to open PDF: {e}"

    try:
        total_pages = len(doc)
        pages_to_read = min(max_pages, total_pages) if max_pages > 0 else total_pages

        text_parts = [f"**PDF: {os.path.basename(file_path)}** ({total_pages} pages)\n"]
        for i in range(pages_to_read):
            page = doc[i]
            text = page.get_text()
            if text.strip():
                text_parts.append(f"\n--- Page {i + 1} ---\n{text}")
    finally:
        doc.close()

    return "\n".join(text_parts)


@mcp.tool()
async def extract_paper_structure(file_path: str) -> str:
    """Extract structured sections from an academic paper PDF (title, abstract, sections, references).

    Args:
        file_path: Absolute path to the PDF file
    """
    fitz = _get_fitz()
    file_path = os.path.expanduser(file_path)
    if not os.path.exists(file_path):
        return f"Error: File not found: {file_path}"

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        return f"Error: Failed to open PDF: {e}"

    try:
        # Extract full text
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
    finally:
        doc.close()

    lines = full_text.split("\n")

    # Heuristic extraction
    title = ""
    abstract = ""
    sections = []
    references_start = -1

    # Title: usually the first non-empty, non-short lines
    for i, line in enumerate(lines[:20]):
        stripped = line.strip()
        if stripped and len(stripped) > 10:
            title = stripped
            break

    # Abstract
    in_abstract = False
    abstract_lines = []
    for line in lines:
        stripped = line.strip().lower()
        if stripped.startswith("abstract"):
            in_abstract = True
            # Handle "Abstract: ..." on same line
            rest = line.strip()[8:].strip().lstrip(":").lstrip("—").lstrip("-").strip()
            if rest:
                abstract_lines.append(rest)
            continue
        if in_abstract:
            if any(stripped.startswith(kw) for kw in ["1 ", "1.", "introduction", "keywords", "key words"]):
                break
            if line.strip():
                abstract_lines.append(line.strip())
    abstract = " ".join(abstract_lines)

    # Section headings (numbered like "1.", "2.", "1 Introduction", etc.)
    section_pattern = re.compile(r"^(\d+\.?\s+[A-Z])")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if section_pattern.match(stripped) and len(stripped) < 100:
            sections.append(stripped)
        if stripped.lower() in ["references", "bibliography"]:
            references_start = i

    # References count
    ref_count = 0
    if references_start > 0:
        ref_pattern = re.compile(r"^\[?\d+\]?\s")
        for line in lines[references_start:]:
            if ref_pattern.match(line.strip()):
                ref_count += 1

    result = f"**Title:** {title}\n\n"
    result += f"**Abstract:** {abstract[:1000]}\n\n"
    result += f"**Sections:**\n"
    for s in sections:
        result += f"  - {s}\n"
    result += f"\n**References:** ~{ref_count} items"
    return result


@mcp.tool()
async def extract_tables_and_figures(file_path: str) -> str:
    """List tables and figures found in a PDF paper (by caption detection).

    Args:
        file_path: Absolute path to the PDF file
    """
    fitz = _get_fitz()
    file_path = os.path.expanduser(file_path)
    if not os.path.exists(file_path):
        return f"Error: File not found: {file_path}"

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        return f"Error: Failed to open PDF: {e}"

    try:
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"

        # Count images
        image_count = 0
        for page in doc:
            image_count += len(page.get_images())
    finally:
        doc.close()

    # Find figure and table captions
    lines = full_text.split("\n")
    figures = []
    tables = []

    fig_pattern = re.compile(r"^(Fig\.?|Figure)\s*\.?\s*(\d+)", re.IGNORECASE)
    table_pattern = re.compile(r"^(Table)\s*\.?\s*(\d+)", re.IGNORECASE)

    for line in lines:
        stripped = line.strip()
        if fig_pattern.match(stripped):
            figures.append(stripped[:150])
        elif table_pattern.match(stripped):
            tables.append(stripped[:150])

    result = f"**Embedded images:** {image_count}\n\n"
    result += f"**Figures ({len(figures)}):**\n"
    for f in figures:
        result += f"  - {f}\n"
    result += f"\n**Tables ({len(tables)}):**\n"
    for t in tables:
        result += f"  - {t}\n"
    return result


if __name__ == "__main__":
    mcp.run()
