"""
NyayaLens — Startup & Corpus Seeding
Runs on FastAPI startup:
  1. Validates GOOGLE_API_KEY is real (not placeholder)
  2. Checks if ChromaDB collection is empty
  3. If empty, seeds corpus from judgments.json automatically
  4. Logs seeding status to console
"""
from __future__ import annotations

import asyncio
import logging
import os

logger = logging.getLogger(__name__)


async def seed_corpus_if_empty() -> None:
    """Auto-seed ChromaDB on first startup if collection is empty."""
    try:
        from app.config import CHROMA_DB_PATH, GOOGLE_API_KEY

        # Don't seed if key is placeholder
        if not GOOGLE_API_KEY or GOOGLE_API_KEY in ("your_key_here", "your_google_api_key_here", ""):
            logger.warning(
                "⚠️  GOOGLE_API_KEY is not set or is a placeholder — skipping corpus seeding. "
                "Add your real key to .env and restart the server."
            )
            return

        import chromadb

        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        try:
            collection = chroma_client.get_collection("judgments")
            count = collection.count()
            if count > 0:
                logger.info("✅ ChromaDB corpus already seeded with %d documents — skipping.", count)
                return
        except Exception:
            # Collection doesn't exist yet — will be created during seeding
            pass

        logger.info("📚 ChromaDB collection is empty — seeding corpus from judgments.json …")
        from app.legal_data.corpus_builder import build_corpus
        await build_corpus()
        logger.info("✅ Corpus seeding complete.")

    except Exception as exc:
        logger.error("Corpus seeding error: %s — server will continue without RAG corpus.", exc)
