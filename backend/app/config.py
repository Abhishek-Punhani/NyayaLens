import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")

if not GOOGLE_API_KEY:
    import warnings
    warnings.warn(
        "GOOGLE_API_KEY is not set. Add it to .env — server will start but LLM calls will fail.",
        RuntimeWarning,
        stacklevel=2,
    )

# ---------------------------------------------------------------------------
# Latest Gemini Models (September 2026)
# ---------------------------------------------------------------------------
MODEL_VOICE  = os.getenv("MODEL_VOICE", "gemini-3.1-flash-live-preview")   # Realtime audio dialog
MODEL_PRO    = os.getenv("MODEL_PRO",   "gemini-3.1-pro-preview")          # Deep legal reasoning
MODEL_FLASH  = os.getenv("MODEL_FLASH", "gemini-3.7-flash")                # Fast extraction agents

# ---------------------------------------------------------------------------
# Storage & Paths
# ---------------------------------------------------------------------------
CHROMA_DB_PATH          = os.getenv("CHROMA_DB_PATH", "./chroma_db")
SQLITE_CHECKPOINT_PATH  = os.getenv("SQLITE_CHECKPOINT_PATH", "./checkpoints.db")
CORPUS_PATH             = os.getenv("CORPUS_PATH", "./app/legal_data/judgments.json")
