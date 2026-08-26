"""RAG Ingestion Pipeline

Reads operational markdown documents from rag/documents/ subdirectories
and indexes them with rich metadata for contextual evidence retrieval.
"""

from pathlib import Path
from typing import List, Dict
import json
import re

DOCS_DIR = Path(__file__).resolve().parent / "documents"
INDEX_FILE = Path(__file__).resolve().parent / "index_manifest.json"


def extract_metadata_from_content(content: str) -> Dict[str, str]:
    """Extracts structured key-values (service, timestamp, version, severity) from markdown headers."""
    meta = {}
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("- **") or line.startswith("**"):
            match = re.match(r"[-*]*\s*\*\*([^*]+)\*\*:\s*`?([^`*]+)`?", line)
            if match:
                key = match.group(1).strip().lower().replace(" ", "_").replace("/", "_")
                val = match.group(2).strip()
                meta[key] = val
    return meta


def load_documents() -> List[Dict[str, Any]]:
    """Crawls rag/documents/ and returns document chunks with parsed metadata."""
    docs = []
    if not DOCS_DIR.exists():
        return docs

    for category_dir in DOCS_DIR.iterdir():
        if category_dir.is_dir():
            category = category_dir.name
            for file_path in category_dir.glob("*.md"):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                extracted_meta = extract_metadata_from_content(content)
                first_line = content.splitlines()[0].replace("#", "").strip() if content.splitlines() else file_path.stem

                docs.append({
                    "id": f"{category}_{file_path.stem}",
                    "category": category,
                    "title": first_line,
                    "filename": file_path.name,
                    "path": str(file_path),
                    "service": extracted_meta.get("service", extracted_meta.get("impacted_systems", "all")),
                    "timestamp": extracted_meta.get("timestamp", extracted_meta.get("date___time", extracted_meta.get("time_window", "Recent"))),
                    "version": extracted_meta.get("version", ""),
                    "severity": extracted_meta.get("severity", "Medium"),
                    "content": content,
                })
    return docs


def ingest_documents():
    """Ingests all operational documents into index manifest / ChromaDB."""
    print("Beginning document ingestion from:", DOCS_DIR)
    docs = load_documents()
    print(f"Found {len(docs)} documents across categories.")

    # 1. Save manifest index
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2)

    # 2. ChromaDB indexing if available
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(Path(__file__).resolve().parent / "chroma_db"))
        collection = client.get_or_create_collection(name="operational_evidence")
        
        if docs:
            collection.upsert(
                ids=[d["id"] for d in docs],
                documents=[d["content"] for d in docs],
                metadatas=[
                    {
                        "category": d["category"],
                        "title": d["title"],
                        "filename": d["filename"],
                        "service": d["service"],
                        "timestamp": str(d["timestamp"]),
                    }
                    for d in docs
                ],
            )
        print("ChromaDB vector store indexed successfully.")
    except Exception as e:
        print(f"ChromaDB persistent indexing notice (using rich manifest index fallback): {e}")

    print("Document ingestion completed.")


if __name__ == "__main__":
    ingest_documents()
