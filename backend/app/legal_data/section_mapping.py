"""
NyayaLens — Verified Section Mapping Table
IPC/CrPC/IEA  →  BNS/BNSS/BSA (effective 1 July 2024)

Confidence levels:
  "verified"       — confirmed by multiple concordant authoritative sources this session
  "single_source"  — only one secondary source seen; flag for advocate verification before use
  "unverified"     — not independently confirmed; must NOT appear in any agent output without advocate sign-off

Rule: the EVENT DATE (not today's date, not the filing date) governs which code applies.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

# ---------------------------------------------------------------------------
# Core mapping table
# ---------------------------------------------------------------------------

SECTION_MAPPING: dict[str, str] = {
    # ── Substantive Law: IPC → BNS ──────────────────────────────────────────
    "IPC 302":  "BNS 103",      # Murder
    "IPC 304A": "BNS 106",      # Death by negligence (includes hit-and-run sub-clause)
    "IPC 279":  "BNS 281",      # Rash/negligent driving
    "IPC 405":  "BNS 316",      # Criminal breach of trust
    "IPC 406":  "BNS 316",      # CBT by carrier / bailee (same BNS section, sub-clause)
    "IPC 420":  "BNS 318",      # Cheating and dishonestly inducing delivery of property
    "IPC 441":  "BNS 329",      # Criminal trespass
    "IPC 442":  "BNS 329",      # House trespass (sub-clause of BNS 329)
    "IPC 447":  "BNS 329",      # Punishment for criminal trespass (absorbed into BNS 329)
    "IPC 503":  "BNS 351",      # Criminal intimidation  ⚠ single_source — see note
    "IPC 506":  "BNS 351",      # Punishment for criminal intimidation ⚠ single_source

    # ── Procedural Law: CrPC → BNSS ─────────────────────────────────────────
    "CrPC 154": "BNSS 173",     # FIR registration (now includes 14-day preliminary enquiry)
    "CrPC 156": "BNSS 175",     # Police investigation without magistrate order
    "CrPC 482": "BNSS 528",     # Inherent powers of High Court
    "CrPC 438": "BNSS 482",     # Anticipatory bail
    "CrPC 439": "BNSS 483",     # Special powers re: bail

    # ── Evidence Law: IEA → BSA ──────────────────────────────────────────────
    "IEA 65B":  "BSA 63",       # Electronic evidence (dual-signature + hash certificate)
    "IEA 57":   "BSA 52",       # Primary electronic evidence (no certificate needed)
    "IEA 101":  "BSA 96",       # Burden of proof
    "IEA 102":  "BSA 97",       # On whom burden of proof lies
}

# ---------------------------------------------------------------------------
# Confidence levels for each mapping
# ---------------------------------------------------------------------------

SECTION_CONFIDENCE: dict[str, Literal["verified", "single_source", "unverified"]] = {
    "IPC 302":  "verified",
    "IPC 304A": "verified",
    "IPC 279":  "verified",
    "IPC 405":  "verified",
    "IPC 406":  "verified",
    "IPC 420":  "verified",
    "IPC 441":  "verified",
    "IPC 442":  "verified",
    "IPC 447":  "verified",
    "IPC 503":  "single_source",   # IPC 503/506 → BNS 351 seen in one secondary source only
    "IPC 506":  "single_source",   # ⚠ advocate verification required before use in any output
    "CrPC 154": "verified",
    "CrPC 156": "verified",
    "CrPC 482": "verified",
    "CrPC 438": "verified",
    "CrPC 439": "verified",
    "IEA 65B":  "verified",
    "IEA 57":   "verified",
    "IEA 101":  "verified",
    "IEA 102":  "verified",
}

# Human-readable notes for display in the observability dashboard
SECTION_NOTES: dict[str, str] = {
    "IPC 503":  "⚠ BNS §351 mapping confirmed by one secondary source only — advocate verification required before citing in any pleading or report.",
    "IPC 506":  "⚠ Same note as IPC §503 — BNS §351 carries forward both intimidation sections per that source.",
    "IPC 442":  "House trespass is a sub-clause within BNS §329; no separate section exists in BNS.",
    "IPC 447":  "BNS §329 consolidates the criminal-trespass family of offences.",
    "IEA 65B":  "BSA §63 requires dual-signatory certificate (device custodian + technical expert) including hash value of the electronic record.",
    "IEA 57":   "BSA §57 covers primary electronic evidence (output of a device in the user's control) — no §63 certificate needed.",
}

# ---------------------------------------------------------------------------
# Dynamic Statute Lookup via statute_db (civictech_db JSON dataset)
# All statutory text and titles are retrieved dynamically from the database.
# ---------------------------------------------------------------------------

from app.legal_data.statute_db import get_section as get_statute_section, get_citation_string


def get_section_details(act: str, section: str) -> Optional[dict]:
    """Retrieve section metadata directly from civictech_db via statute_db."""
    return get_statute_section(act, section)


# ---------------------------------------------------------------------------
# Core utility: determine applicable law from event date
# ---------------------------------------------------------------------------

_BNS_COMMENCEMENT = date(2024, 7, 1)   # BNS / BNSS / BSA effective date


def get_applicable_law(
    event_date_str: Optional[str],
) -> Literal["pre_2024_codes", "post_2024_codes", "mixed", "unknown"]:
    """
    Given a free-text event date string, return the applicable law context.

    Returns:
        "pre_2024_codes"  — event definitively before 1 Jul 2024
        "post_2024_codes" — event definitively on/after 1 Jul 2024
        "mixed"           — multiple events spanning the transition (pass a comma-separated list)
        "unknown"         — date unparseable or not provided
    """
    if not event_date_str:
        return "unknown"

    # Support comma-separated list for cases spanning multiple events
    parts = [p.strip() for p in event_date_str.split(",") if p.strip()]
    results: set[str] = set()

    for part in parts:
        try:
            # Normalise: strip time component, handle Z suffix
            normalised = part.replace("Z", "").split("T")[0].split(" ")[0]
            parsed = datetime.strptime(normalised, "%Y-%m-%d").date()
            if parsed < _BNS_COMMENCEMENT:
                results.add("pre_2024_codes")
            else:
                results.add("post_2024_codes")
        except (ValueError, AttributeError):
            results.add("unknown")

    if not results:
        return "unknown"
    if "unknown" in results and len(results) == 1:
        return "unknown"
    # Filter out "unknown" for the mixed check
    known = results - {"unknown"}
    if len(known) > 1:
        return "mixed"
    if known:
        return known.pop()  # type: ignore[return-value]
    return "unknown"


def map_section(old_section: str) -> str:
    """Map an old IPC/CrPC/IEA section to its BNS/BNSS/BSA equivalent."""
    return SECTION_MAPPING.get(old_section, old_section)


def get_confidence(old_section: str) -> Literal["verified", "single_source", "unverified"]:
    """Return confidence level for a given mapping."""
    return SECTION_CONFIDENCE.get(old_section, "unverified")
