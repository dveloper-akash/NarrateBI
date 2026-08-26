"""RAG Retrieval Module

Provides a simple interface: retrieve_evidence(query, top_k=5)
returning a list of relevant operational evidence objects.
"""

from pathlib import Path
from typing import List, Optional
import json
from engine.evidence import EvidenceItem

INDEX_FILE = Path(__file__).resolve().parent / "index_manifest.json"
CHROMA_DIR = Path(__file__).resolve().parent / "chroma_db"


def retrieve_evidence(query: str, top_k: int = 4) -> List[EvidenceItem]:
    """Retrieves top relevant operational evidence documents for the query."""
    results: List[EvidenceItem] = []

    # 1. Attempt ChromaDB vector retrieval
    try:
        import chromadb
        if CHROMA_DIR.exists():
            client = chromadb.PersistentClient(path=str(CHROMA_DIR))
            collection = client.get_collection(name="operational_evidence")
            query_res = collection.query(query_texts=[query], n_results=top_k)
            
            docs = query_res.get("documents", [[]])[0]
            metas = query_res.get("metadatas", [[]])[0]

            for doc_text, meta in zip(docs, metas):
                category = meta.get("category", "Operations").capitalize()
                lines = [l.strip() for l in doc_text.splitlines() if l.strip()]
                title = lines[0] if lines else "Operational note"
                results.append(
                    EvidenceItem(
                        source=category,
                        timestamp="Recent",
                        description=f"{title.replace('#', '').strip()}: {lines[1] if len(lines) > 1 else ''}",
                        relevance="High",
                        is_structured=False,
                    )
                )
            if results:
                return results
    except Exception:
        pass

    # 2. Fallback to manifest keyword search
    if INDEX_FILE.exists():
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        
        q_lower = query.lower()
        scored_docs = []
        for doc in manifest:
            content = doc.get("content", "").lower()
            score = sum(1 for word in q_lower.split() if word in content)
            scored_docs.append((score, doc))

        scored_docs.sort(key=lambda x: x[0], reverse=True)

        for _, doc in scored_docs[:top_k]:
            category = doc.get("category", "Operations").capitalize()
            content_lines = [l.strip() for l in doc.get("content", "").splitlines() if l.strip()]
            summary = content_lines[0].replace("#", "").strip() if content_lines else doc.get("filename", "")
            results.append(
                EvidenceItem(
                    source=category,
                    timestamp="Recent",
                    description=summary,
                    relevance="High",
                    is_structured=False,
                )
            )

    return results
