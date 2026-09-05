import os
import json
import asyncio
import logging
import chromadb
from google import genai
from app.config import CHROMA_DB_PATH, CORPUS_PATH, GOOGLE_API_KEY

logger = logging.getLogger(__name__)

async def build_corpus():
    if not os.path.exists(CORPUS_PATH):
        print(f"Corpus file not found at {CORPUS_PATH}")
        return

    if not GOOGLE_API_KEY:
        print("GOOGLE_API_KEY is not set. Please provide API key in .env to embed corpus.")
        return

    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_or_create_collection(name="judgments")
    genai_client = genai.Client(api_key=GOOGLE_API_KEY)

    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        try:
            judgments = json.load(f)
        except json.JSONDecodeError:
            print("Invalid JSON in corpus file.")
            return

    count = 0
    for doc in judgments:
        source_id = doc.get("source_id") or doc.get("id") or f"doc_{count}"
        exact_citation = doc.get("exact_citation") or doc.get("title", "")
        supporting_passage = doc.get("supporting_passage") or doc.get("holding", "")
        text = f"{exact_citation}. {supporting_passage}"

        if not text.strip():
            continue

        metadata = {
            "source_id": str(source_id),
            "exact_citation": str(exact_citation),
            "source_url": str(doc.get("source_url", "")),
            "court": str(doc.get("jurisdiction", doc.get("court", "Supreme Court of India"))),
            "date": str(doc.get("date", doc.get("year", "unknown"))),
            "applicability_status": str(doc.get("applicability_status", "good_law")),
            "contradiction_or_limit": str(doc.get("contradiction_or_limit", "")),
            "case_type": "property_dispute",
            "law_version": str(doc.get("law_version", "pre_2024_codes")),
        }

        try:
            response = genai_client.models.embed_content(
                model="gemini-embedding-2",
                contents=text,
            )
            embedding = response.embeddings[0].values
            collection.upsert(
                documents=[text],
                metadatas=[metadata],
                ids=[str(source_id)],
                embeddings=[embedding],
            )
            count += 1
        except Exception as e:
            logger.error(f"Error embedding {source_id}: {e}")

    print(f"Corpus built successfully with {count} judgments.")

def search_corpus(query: str, case_type: str = "property_dispute", law_version: str = "unknown", n_results: int = 5) -> list[dict]:
    if not os.path.exists(CHROMA_DB_PATH) or not GOOGLE_API_KEY:
        return []

    try:
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = client.get_collection(name="judgments")
        genai_client = genai.Client(api_key=GOOGLE_API_KEY)

        response = genai_client.models.embed_content(
            model="gemini-embedding-2",
            contents=query,
        )
        query_embedding = response.embeddings[0].values

        # Build filter if law_version is known
        where_filter = None
        if law_version in ("pre_2024_codes", "post_2024_codes"):
            where_filter = {"law_version": law_version}

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
        )

        formatted_results = []
        if results.get("documents") and len(results["documents"]) > 0:
            for i in range(len(results["documents"][0])):
                formatted_results.append({
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                })
        return formatted_results
    except Exception as exc:
        logger.warning(f"ChromaDB search fallback: {exc}")
        return []

if __name__ == "__main__":
    asyncio.run(build_corpus())
