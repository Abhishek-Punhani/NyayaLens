"""
NyayaLens — Indian Law Static JSON Loader
==========================================
Loads the civictech-India/Indian-Law-Penal-Code-Json dataset.
Zero hardcoded statutory text. All text comes from the JSON files.

Source: https://github.com/civictech-India/Indian-Law-Penal-Code-Json
Files:  backend/app/legal_data/civictech_db/

Available Acts (old codes — applies to events before 01-Jul-2024):
  IPC   Indian Penal Code, 1860              (575 sections)
  IEA   Indian Evidence Act, 1872            (184 sections)
  CRPC  Code of Criminal Procedure, 1973     (525 sections)
  CPC   Code of Civil Procedure, 1908        (171 sections)
  MVA   Motor Vehicles Act, 1988             (256 sections)
  HMA   Hindu Marriage Act, 1955             (283 entries)
  IDA   Indian Divorce Act, 1869              (64 sections)
  NIA   Negotiable Instruments Act, 1881     (156 sections)

For new codes (BNS/BNSS/BSA 2023, events on/after 01-Jul-2024):
  Sections are fetched live from Indian Kanoon API (doctypes:laws)
  using the research_query tool in the statute_analysis_node.

The LLM is given a compact index (section_number + title) to decide
what to pick. Full text is fetched only for the chosen sections.
"""
from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DB_DIR = Path(__file__).parent / "civictech_db"

ACT_LABELS: dict[str, str] = {
    "IPC":  "Indian Penal Code, 1860",
    "IEA":  "Indian Evidence Act, 1872",
    "CRPC": "Code of Criminal Procedure, 1973",
    "CPC":  "Code of Civil Procedure, 1908",
    "MVA":  "Motor Vehicles Act, 1988",
    "HMA":  "Hindu Marriage Act, 1955",
    "IDA":  "Indian Divorce Act, 1869",
    "NIA":  "Negotiable Instruments Act, 1881",
    # New codes — fetched live from Indian Kanoon
    "BNS":  "Bharatiya Nyaya Sanhita, 2023",
    "BNSS": "Bharatiya Nagarik Suraksha Sanhita, 2023",
    "BSA":  "Bharatiya Sakshya Adhiniyam, 2023",
}

# Which acts come from local JSON vs Indian Kanoon API
LOCAL_ACTS = {"IPC", "IEA", "CRPC", "CPC", "MVA", "HMA", "IDA", "NIA"}
LIVE_ACTS  = {"BNS", "BNSS", "BSA"}


# ---------------------------------------------------------------------------
# Loader — normalises all schema variants into a uniform dict
# ---------------------------------------------------------------------------

def _normalise(entry: dict) -> dict:
    section = str(entry.get("Section") or entry.get("section") or "").strip()
    title   = str(entry.get("section_title") or entry.get("title") or "").strip()
    desc    = str(entry.get("section_desc")  or entry.get("description") or "").strip()
    chapter = str(entry.get("chapter") or "").strip()
    chapter_title = str(entry.get("chapter_title") or "").strip()
    return {
        "section_number": section,
        "section_title": title,
        "section_desc": desc,
        "chapter": chapter,
        "chapter_title": chapter_title,
    }


def _load(filename: str) -> dict[str, dict]:
    path = _DB_DIR / filename
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        logger.error("[StatuteDB] Missing file: %s", path)
        return {}
    except Exception as e:
        logger.error("[StatuteDB] Load error %s: %s", filename, e)
        return {}

    if not isinstance(raw, list):
        return {}

    indexed: dict[str, dict] = {}
    for entry in raw:
        # hma.json packs CSV into a single key — unwrap it
        keys = list(entry.keys())
        if len(keys) == 1 and "," in keys[0]:
            header = keys[0].split(",")
            value  = list(entry.values())[0]
            try:
                row = next(csv.reader([value]))
                if len(row) == len(header):
                    entry = dict(zip(header, row))
                else:
                    continue
            except Exception:
                continue

        norm = _normalise(entry)
        key  = norm["section_number"]
        if key:
            indexed[key] = norm

    logger.info("[StatuteDB] %s → %d sections", filename, len(indexed))
    return indexed


# In-memory indexes (loaded once at import)
_DB: dict[str, dict[str, dict]] = {
    "IPC":  _load("ipc.json"),
    "IEA":  _load("iea.json"),
    "CRPC": _load("crpc.json"),
    "CPC":  _load("cpc.json"),
    "MVA":  _load("MVA.json"),
    "HMA":  _load("hma.json"),
    "IDA":  _load("ida.json"),
    "NIA":  _load("nia.json"),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_section(act: str, section: str) -> Optional[dict]:
    """
    Fetch a single section's full text from the local DB.
    Returns normalised dict or None if not found.
    Only works for LOCAL_ACTS — for BNS/BNSS/BSA use Indian Kanoon API.
    """
    idx = _DB.get(act.upper())
    if idx is None:
        return None
    return idx.get(str(section).strip())


def get_section_index(act: str) -> list[dict]:
    """
    Return a compact index for an act: [{section_number, section_title}, ...]
    This is the 'menu' given to the LLM so it can pick relevant sections
    without loading full text for thousands of sections.
    """
    idx = _DB.get(act.upper(), {})
    return [
        {"section_number": e["section_number"], "section_title": e["section_title"]}
        for e in idx.values()
        if e["section_number"]
    ]


def get_citation_string(act: str, section: str) -> str:
    """Return formatted citation: 'Section X, <Full Act Name>'"""
    label = ACT_LABELS.get(act.upper(), act)
    return f"Section {section}, {label}"


def db_stats() -> dict[str, int]:
    """Return total section counts per act — useful for health checks / logging."""
    return {act: len(idx) for act, idx in _DB.items()}
