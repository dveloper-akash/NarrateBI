"""RAG Retrieval Module

Provides a simple, reliable interface:
retrieve_evidence(query, top_k=4, category=None)
returning a list of relevant operational evidence objects.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
import json
from engine.evidence import EvidenceItem

INDEX_FILE = Path(__file__).resolve().parent / "index_manifest.json"
CHROMA_DIR = Path(__file__).resolve().parent / "chroma_db"


def retrieve_evidence(
    query: str,
    top_k: int = 4,
    category: Optional[str] = None,
) -> List[EvidenceItem]:
    """Retrieves top relevant operational evidence documents matching the query."""
    results: List[EvidenceItem] = []

    # 1. Attempt ChromaDB vector retrieval
    try:
        import chromadb
        if CHROMA_DIR.exists():
            client = chromadb.PersistentClient(path=str(CHROMA_DIR))
            collection = client.get_collection(name="operational_evidence")
            where_clause = {"category": category} if category else None
            
            query_res = collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_clause,
            )
            
            docs = query_res.get("documents", [[]])[0]
            metas = query_res.get("metadatas", [[]])[0]

            for doc_text, meta in zip(docs, metas):
                cat = meta.get("category", "operations").capitalize()
                title = meta.get("title", "Operational Log")
                timestamp = meta.get("timestamp", "Recent")
                
                # Extract first substantive bullet or line
                summary_line = ""
                for line in doc_text.splitlines():
                    clean_line = line.strip().lstrip("#-* ").strip()
                    if clean_line and clean_line != title and not clean_line.startswith("**"):
                        summary_line = clean_line
                        break
                
                desc = f"{title}: {summary_line}" if summary_line else title

                results.append(
                    EvidenceItem(
                        source=cat,
                        timestamp=timestamp,
                        description=desc,
                        relevance="High",
                        is_structured=False,
                    )
                )
            if results:
                return results
    except Exception:
        pass

    # 2. Resilient Manifest Search (Ranked TF matching)
    if INDEX_FILE.exists():
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            manifest: List[Dict[str, Any]] = json.load(f)

        query_tokens = [t.lower() for t in query.replace("-", " ").replace("_", " ").split() if len(t) > 2]
        scored_docs = []

        for doc in manifest:
            if category and doc.get("category") != category:
                continue

            content = doc.get("content", "").lower()
            title = doc.get("title", "").lower()
            service = doc.get("service", "").lower()

            score = 0
            for token in query_tokens:
                if token in title:
                    score += 5
                if token in service:
                    score += 4
                if token in content:
                    score += 1

            if score > 0 or not query_tokens:
                scored_docs.append((score, doc))

        scored_docs.sort(key=lambda x: x[0], reverse=True)

        for _, doc in scored_docs[:top_k]:
            cat = doc.get("category", "operations").capitalize()
            title = doc.get("title", "Operational Note")
            timestamp = doc.get("timestamp", "Recent")
            
            # Find representative summary line
            summary_line = ""
            for line in doc.get("content", "").splitlines():
                clean = line.strip().lstrip("#-* ").strip()
                if clean and clean != title and not clean.startswith("**"):
                    summary_line = clean
                    break
            
            desc = f"{title}: {summary_line}" if summary_line else title

            results.append(
                EvidenceItem(
                    source=cat,
                    timestamp=timestamp,
                    description=desc,
                    relevance="High" if _ > 2 else "Medium",
                    is_structured=False,
                )
            )

    return results
