"""
NyayaLens — Indian Kanoon API Client
=====================================
Provides live legal research using the official Indian Kanoon API.
Authenticated via API token (Authorization: Token <token>).

Endpoints used:
  - POST https://api.indiankanoon.org/search/  → search judgments
  - POST https://api.indiankanoon.org/doc/<id>/  → fetch full judgment

The search returns JSON with a `docs` array. Each doc has:
  tid, title, headline, docsource, publishdate, docsize, numcites

The document fetch returns JSON with a `doc` HTML field (full judgment text)
plus metadata: title, docsource, publishdate, citeList, citedbyList.

Rate Limits (per IK docs): requests are metered by credits (₹0.50/search, ₹0.20/doc)
We cap queries per session and use async httpx for non-blocking calls.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import httpx

from app.config import INDIAN_KANOON_TOKEN

logger = logging.getLogger(__name__)

_IK_BASE     = "https://api.indiankanoon.org"
_TIMEOUT     = httpx.Timeout(15.0, connect=5.0)
_MAX_RESULTS = 5   # top N search results to consider per query
_MAX_DOC_FETCH = 2  # full document fetch per query (cost control)


def _auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Token {INDIAN_KANOON_TOKEN}",
        "Accept": "application/json",
    }


def _strip_html(html: str) -> str:
    """Remove all HTML tags and collapse whitespace to get plain text."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


async def search_judgments(query: str, doctypes: str = "judgments", max_results: int = _MAX_RESULTS) -> list[dict[str, Any]]:
    """
    Search Indian Kanoon for judgments matching the query.
    Returns a list of result dicts with keys: tid, title, headline, docsource, publishdate.

    doctypes options:
      - "supremecourt"  → only Supreme Court
      - "judgments"     → SC + HCs + District Courts
      - "laws"          → bare acts only
    """
    if not INDIAN_KANOON_TOKEN:
        logger.error("[IndianKanoon] No API token configured. Set INDIAN_KANOON_TOKEN in .env")
        return []

    params = {
        "formInput": f"{query} doctypes:{doctypes}",
        "pagenum": 0,
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{_IK_BASE}/search/",
                headers=_auth_headers(),
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
            docs = data.get("docs", [])[:max_results]
            logger.info("[IndianKanoon] Search '%s' → %d results (total found: %s)", query, len(docs), data.get("found", "?"))
            return docs
    except httpx.HTTPStatusError as e:
        logger.error("[IndianKanoon] Search HTTP error %s for query '%s': %s", e.response.status_code, query, e)
        return []
    except Exception as e:
        logger.error("[IndianKanoon] Search error for query '%s': %s", query, e)
        return []


async def fetch_document(tid: str | int) -> dict[str, Any] | None:
    """
    Fetch the full text of a judgment from Indian Kanoon by document ID (tid).
    Returns dict with keys: title, docsource, publishdate, doc (full HTML text), citeList, citedbyList.
    Returns None on failure.
    """
    if not INDIAN_KANOON_TOKEN:
        return None

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{_IK_BASE}/doc/{tid}/",
                headers=_auth_headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info("[IndianKanoon] Fetched doc %s — '%s'", tid, data.get("title", ""))
            return data
    except httpx.HTTPStatusError as e:
        logger.error("[IndianKanoon] Doc fetch HTTP error %s for tid '%s': %s", e.response.status_code, tid, e)
        return None
    except Exception as e:
        logger.error("[IndianKanoon] Doc fetch error for tid '%s': %s", tid, e)
        return None


async def research_query(query: str, doctypes: str = "judgments") -> list[dict[str, Any]]:
    """
    High-level: search for a query, then fetch full text of top N docs.
    Returns a list of enriched citation dicts ready for CitationRecord building:
      - source_id, exact_citation, source_url, supporting_passage,
        jurisdiction, date, full_text (first 800 chars of cleaned judgment)
    """
    search_results = await search_judgments(query, doctypes=doctypes, max_results=_MAX_RESULTS)
    if not search_results:
        return []

    enriched = []

    # Fetch full docs for top _MAX_DOC_FETCH results concurrently
    top_docs = search_results[:_MAX_DOC_FETCH]
    tasks = [fetch_document(doc["tid"]) for doc in top_docs]
    fetched_docs = await asyncio.gather(*tasks, return_exceptions=True)

    for i, doc_data in enumerate(fetched_docs):
        search_hit = search_results[i]
        tid = search_hit.get("tid", "")
        title = search_hit.get("title", "")
        docsource = search_hit.get("docsource", "India")
        publishdate = search_hit.get("publishdate", "")
        headline_html = search_hit.get("headline", "")
        headline_text = _strip_html(headline_html)[:400]

        full_text = ""
        if isinstance(doc_data, dict):
            raw_html = doc_data.get("doc", "")
            full_text = _strip_html(raw_html)[:800]

        # Extract a short year from publishdate "DD-MM-YYYY"
        year = ""
        if publishdate and "-" in publishdate:
            parts = publishdate.split("-")
            year = parts[-1] if len(parts) >= 3 else publishdate

        status_type = "statute" if doctypes == "laws" else "case_law"
        enriched.append({
            "source_id": f"IK_{tid}",
            "exact_citation": title,
            "source_url": f"https://indiankanoon.org/doc/{tid}/",
            "supporting_passage": full_text or headline_text,
            "jurisdiction": docsource,
            "date": year or publishdate,
            "applicability_status": status_type,
        })

    # For remaining search results (no full fetch), use headline only
    for doc in search_results[_MAX_DOC_FETCH:]:
        tid = doc.get("tid", "")
        title = doc.get("title", "")
        headline_text = _strip_html(doc.get("headline", ""))[:400]
        publishdate = doc.get("publishdate", "")
        year = publishdate.split("-")[-1] if publishdate and "-" in publishdate else publishdate

        status_type = "statute" if doctypes == "laws" else "case_law"
        enriched.append({
            "source_id": f"IK_{tid}",
            "exact_citation": title,
            "source_url": f"https://indiankanoon.org/doc/{tid}/",
            "supporting_passage": headline_text,
            "jurisdiction": doc.get("docsource", "India"),
            "date": year,
            "applicability_status": status_type,
        })

    return enriched
