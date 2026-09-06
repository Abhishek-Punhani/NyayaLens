"""
NyayaLens — OCR / Document Intelligence Agent
Uses Gemini Vision (gemini-2.5-flash) to extract structured legal facts
from uploaded document images. Every extracted fact is tagged
evidence_type="DOCUMENT_EXTRACTED" per the provenance discipline.
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from google import genai
from google.genai import types

from app.config import GOOGLE_API_KEY, MODEL_FLASH
from app.state import DocumentRecord, Fact

logger = logging.getLogger(__name__)

_OCR_PROMPT = """
You are a legal document analyst. Carefully extract information from this
{doc_type} document image. Return ONLY a JSON object with these keys:

{{
  "ocr_text": "full extracted text, verbatim where readable",
  "key_clauses": ["list of important clauses or facts found in the document"],
  "registration_status": "registered | unregistered | unclear",
  "is_registered_mentioned": true/false,
  "names_found": ["list of person names found"],
  "dates_found": ["list of dates found"],
  "property_description": "any description of the property (survey no., address, area)",
  "document_date": "date of the document if found",
  "bsa63_certificate_needed": true/false,
  "bsa63_reason": "why the BSA §63 certificate is or isn't needed",
  "low_confidence": true/false,
  "low_confidence_reason": "if low_confidence is true, why (blurry, rotated, partial, etc.)"
}}

Rules:
- registration_status = "registered" only if the document explicitly says 'Registered' or shows a
  Sub-Registrar stamp/endorsement. If the document mentions the word 'registered' in a different
  context (e.g. 'unregistered deed'), set it to "unregistered".
- bsa63_certificate_needed = true if the document is or mentions: audio recording, video recording,
  WhatsApp message, screenshot, CCTV footage, or any digital/electronic evidence.
  This is required under Section 63, Bharatiya Sakshya Adhiniyam, 2023 (for events on/after 1 Jul 2024)
  or Section 65B, Indian Evidence Act, 1872 (for events before 1 Jul 2024).
- If the image is too blurry, rotated, or incomplete to extract reliably, set low_confidence = true
  and explain in low_confidence_reason.
- Never invent text that is not visible in the document.
- Return ONLY the JSON, no markdown fences.
"""


def _parse_json_block(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    return json.loads(text)


async def extract_document(
    image_bytes: bytes,
    doc_type: str,
    session_id: str,
) -> DocumentRecord:
    """
    Extract structured facts from a document image using Gemini Vision.
    Always returns a DocumentRecord — never raises. Failures are captured
    in upload_status='failed' and limitations_flag.
    """
    doc_id = f"DOC-{uuid.uuid4().hex[:8]}"

    try:
        client = genai.Client(api_key=GOOGLE_API_KEY)

        prompt = _OCR_PROMPT.format(doc_type=doc_type)

        response = client.models.generate_content(
            model=MODEL_FLASH,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                prompt,
            ],
        )

        try:
            parsed = _parse_json_block(response.text)
        except (json.JSONDecodeError, AttributeError):
            logger.warning("OCR agent returned non-JSON for doc_type=%s", doc_type)
            return DocumentRecord(
                doc_id=doc_id,
                doc_type=doc_type,
                ocr_text=response.text if response.text else "",
                upload_status="ocr_done",
                limitations_flag="OCR completed but response was not structured JSON — raw text available",
            )

        # Low-confidence / unreadable
        if parsed.get("low_confidence"):
            return DocumentRecord(
                doc_id=doc_id,
                doc_type=doc_type,
                ocr_text=parsed.get("ocr_text", ""),
                upload_status="failed",
                limitations_flag=f"LOW_OCR_CONFIDENCE — {parsed.get('low_confidence_reason', 'image unclear')}. Please upload a clearer image.",
            )

        # ── Build extracted facts from parsed document ───────────────────────
        extracted_facts: list[Fact] = []
        turn_ref = f"doc_{doc_id}"

        def _make_fact(field: str, value: str, confidence: float = 0.8) -> Fact:
            return Fact(
                fact_id=f"F-{uuid.uuid4().hex[:8]}",
                field=field,
                value=value,
                evidence_type="DOCUMENT_EXTRACTED",
                source_ref=turn_ref,
                confidence=confidence,
                status="unconfirmed",
                contradicts=[],
            )

        # Property identification from document
        if parsed.get("property_description"):
            extracted_facts.append(_make_fact(
                "property_identification",
                parsed["property_description"],
                confidence=0.85,
            ))

        # Document date
        if parsed.get("document_date"):
            extracted_facts.append(_make_fact(
                "document_date",
                parsed["document_date"],
                confidence=0.9,
            ))

        # Names (people mentioned in the document)
        for name in parsed.get("names_found", [])[:5]:  # cap at 5
            extracted_facts.append(_make_fact("person_mentioned_in_doc", name, 0.9))

        # Registration status fact
        reg_status = parsed.get("registration_status", "unclear")
        extracted_facts.append(_make_fact(
            "document_registration_status",
            f"{doc_type}: {reg_status}",
            confidence=0.9 if reg_status != "unclear" else 0.4,
        ))

        # Key clauses as a single fact
        clauses = parsed.get("key_clauses", [])
        if clauses:
            extracted_facts.append(_make_fact(
                "document_key_clauses",
                "; ".join(clauses[:10]),
                confidence=0.75,
            ))

        return DocumentRecord(
            doc_id=doc_id,
            doc_type=doc_type,
            ocr_text=parsed.get("ocr_text", ""),
            extracted_facts=extracted_facts,
            key_clauses=clauses[:10],
            registration_status=reg_status,   # type: ignore[arg-type]
            bsa63_certificate_needed=bool(parsed.get("bsa63_certificate_needed", False)),
            upload_status="ocr_done",
            limitations_flag=None,
        )

    except Exception as exc:
        logger.error("extract_document error (doc_type=%s, session=%s): %s", doc_type, session_id, exc, exc_info=True)
        return DocumentRecord(
            doc_id=doc_id,
            doc_type=doc_type,
            upload_status="failed",
            limitations_flag=f"API error during OCR — please retry. ({type(exc).__name__})",
        )
