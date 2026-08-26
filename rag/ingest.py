"""RAG Ingestion Pipeline

Reads operational markdown documents from rag/documents/ subdirectories
and indexes them for contextual evidence retrieval.
"""

from pathlib import Path
from typing import List, Dict
import json

DOCS_DIR = Path(__file__).resolve().parent / "documents"
INDEX_FILE = Path(__file__).resolve().parent / "index_manifest.json"


def load_documents() -> List[Dict[str, str]]:
    """Crawls rag/documents/ and returns document chunks with metadata."""
    docs = []
    if not DOCS_DIR.exists():
        return docs

    for category_dir in DOCS_DIR.iterdir():
        if category_dir.is_dir():
            category = category_dir.name
            for file_path in category_dir.glob("*.md"):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                docs.append({
                    "id": f"{category}_{file_path.stem}",
                    "category": category,
                    "filename": file_path.name,
                    "path": str(file_path),
                    "content": content,
                })
    return docs


def ingest_documents():
    """Ingests all operational documents into index manifest / ChromaDB."""
    print("Beginning document ingestion from:", DOCS_DIR)
    docs = load_documents()
    print(f"Found {len(docs)} documents across categories.")

    # Save manifest index
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2)

    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(Path(__file__).resolve().parent / "chroma_db"))
        collection = client.get_or_create_collection(name="operational_evidence")
        
        if docs:
            collection.upsert(
                ids=[d["id"] for d in docs],
                documents=[d["content"] for d in docs],
                metadatas=[{"category": d["category"], "filename": d["filename"]} for d in docs],
            )
        print("ChromaDB vector store indexed successfully.")
    except Exception as e:
        print(f"ChromaDB persistent indexing notice (using manifest index fallback): {e}")

    print("Document ingestion completed.")


if __name__ == "__main__":
    ingest_documents()
