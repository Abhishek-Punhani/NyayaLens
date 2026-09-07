"""
NyayaLens — Startup Validation
Runs on FastAPI startup:
  1. Validates GOOGLE_API_KEY is set
  2. Validates INDIAN_KANOON_TOKEN is set
  3. Logs configuration status to console
  (ChromaDB / corpus seeding removed — legal research is now live via Indian Kanoon API)
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def validate_startup_config() -> None:
    """Validate required API keys are configured."""
    from app.config import GOOGLE_API_KEY, INDIAN_KANOON_TOKEN

    placeholders = {"your_key_here", "your_google_api_key_here", "your_indian_kanoon_api_token_here", ""}

    if not GOOGLE_API_KEY or GOOGLE_API_KEY in placeholders:
        logger.warning(
            "⚠️  GOOGLE_API_KEY is not set or is a placeholder — "
            "LLM calls (intake, analysis, argument builder) will fail. "
            "Add your real Gemini API key to backend/.env and restart."
        )
    else:
        logger.info("✅ GOOGLE_API_KEY configured.")

    if not INDIAN_KANOON_TOKEN or INDIAN_KANOON_TOKEN in placeholders:
        logger.warning(
            "⚠️  INDIAN_KANOON_TOKEN is not set or is a placeholder — "
            "Live legal research (precedent_research_node) will return empty citations. "
            "Register at https://api.indiankanoon.org and add your token to backend/.env."
        )
    else:
        logger.info("✅ INDIAN_KANOON_TOKEN configured — live legal research enabled.")
