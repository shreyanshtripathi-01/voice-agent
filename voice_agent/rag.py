"""Retrieval-Augmented Generation (RAG) over a local markdown knowledge base.

This is a real retrieval pipeline: TF-IDF vectors built from the documents at
startup, cosine similarity at query time, and cited source chunks in the reply.
It is intentionally small and offline. A production version would swap in
embeddings + a vector database (see docs/architecture.mmd).
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, List

from .config import KNOWLEDGE_DIR

_SYNONYMS = {
    "cost": {"price", "pricing", "priced", "costs", "rates", "afford", "budget"},
    "price": {"cost", "pricing", "priced", "rates", "afford", "budget"},
    "priced": {"price", "cost", "pricing", "rates"},
    "much": {"price", "cost", "priced"},
    "hindi": {"language", "multilingual", "bilingual"},
    "spanish": {"language", "multilingual", "bilingual"},
    "india": {"multilingual", "hindi"},
    "crm": {"salesforce", "hubspot", "integration", "integrate"},
    "book": {"appointment", "schedule", "meeting"},
    "meeting": {"appointment", "schedule", "book"},
    "safe": {"security", "secure", "privacy", "encrypt"},
    "secure": {"security", "privacy", "encrypt"},
    "data": {"security", "privacy", "storage"},
    "summary": {"summarise", "summarize", "insights"},
    "knowledge": {"rag", "documents", "retrieval"},
}

_TOKEN_RE = re.compile(r"[\w\u0900-\u097F]+")
_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "be", "it", "its", "does", "do", "did", "can",
    "how", "much", "what", "you", "your", "our", "we", "i", "to", "of", "in", "for", "with",
    "on", "and", "or", "this", "that", "have", "has", "about", "please", "would", "could",
}


def tokenize(text: str) -> List[str]:
    return [t for t in _TOKEN_RE.findall((text or "").lower()) if len(t) > 2 and t not in _STOPWORDS]


def _expand(tokens: List[str]) -> List[str]:
    expanded = list(tokens)
    for token in tokens:
        expanded.extend(_SYNONYMS.get(token, ()))
    return expanded


def load_documents(directory=KNOWLEDGE_DIR) -> List[Dict[str, str]]:
    """Load markdown files and split them into heading-level chunks."""
    chunks: List[Dict[str, str]] = []
    for path in sorted(directory.glob("*.md")):
        section = "Overview"
        buffer: List[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                continue  # title is metadata, not content
            if line.startswith("## "):
                if buffer:
                    chunks.append(_chunk(path.stem, section, buffer))
                    buffer = []
                section = line[3:].strip()
            elif line.strip():
                buffer.append(line.strip())
        if buffer:
            chunks.append(_chunk(path.stem, section, buffer))
    return chunks


def _chunk(doc: str, section: str, lines: List[str]) -> Dict[str, str]:
    return {"doc": doc, "section": section, "text": " ".join(lines)}


class KnowledgeBase:
    """Tiny TF-IDF retriever. Thread-safe after construction (read only)."""

    def __init__(self, directory=KNOWLEDGE_DIR):
        self.chunks = load_documents(directory)
        self.doc_tokens = [tokenize(c["text"]) for c in self.chunks]
        n = len(self.chunks)
        df: Counter = Counter()
        for tokens in self.doc_tokens:
            df.update(set(tokens))
        self.idf = {t: math.log((1 + n) / (1 + d)) + 1 for t, d in df.items()}
        self.vectors: List[Dict[str, float]] = []
        for tokens in self.doc_tokens:
            counts = Counter(tokens)
            total = sum(counts.values()) or 1
            self.vectors.append({t: (c / total) * self.idf[t] for t, c in counts.items()})

    def retrieve(self, query: str, top_k: int = 2) -> List[Dict[str, object]]:
        q_tokens = _expand(tokenize(query))
        counts = Counter(q_tokens)
        total = sum(counts.values()) or 1
        q_vec = {t: (c / total) * self.idf.get(t, 1.0) for t, c in counts.items()}
        if not q_vec:
            return []
        results: List[Dict[str, object]] = []
        for chunk, vec in zip(self.chunks, self.vectors):
            shared = set(q_vec) & set(vec)
            dot = sum(q_vec[t] * vec[t] for t in shared)
            q_norm = math.sqrt(sum(v * v for v in q_vec.values()))
            d_norm = math.sqrt(sum(v * v for v in vec.values()))
            score = dot / (q_norm * d_norm) if q_norm and d_norm else 0.0
            if score > 0.02:
                results.append({**chunk, "score": round(score, 3),
                                "source": f"{chunk['doc']}.md → {chunk['section']}"})
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]

    def best_answer(self, query: str) -> str:
        """Combine the two most relevant chunks into one short spoken answer."""
        hits = self.retrieve(query, top_k=2)
        return " ".join(str(hit["text"]) for hit in hits) if hits else ""
