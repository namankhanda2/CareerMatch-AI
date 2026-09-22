"""Lightweight, dependency-free semantic similarity.

Deterministic fallback: no embeddings, no network. We measure token
overlap between the resume and the job description using cosine similarity
over word-frequency counters. Deterministic and fast enough for rounding out
the evidence the matcher already produced.
"""

import re
from collections import Counter

_STOPWORDS = {
    "the", "and", "for", "with", "are", "was", "were", "have", "has", "had",
    "this", "that", "from", "your", "you", "our", "will", "would", "shall",
    "also", "able", "its", "their", "them", "they", "his", "her", "she", "he",
    "can", "could", "should", "all", "any", "who", "what", "when", "where",
    "which", "why", "how", "not", "but", "per", "due", "to", "of", "in", "at",
    "on", "by", "or", "as", "if", "than", "then", "else", "one", "two", "new",
}

_TOKEN_RE = re.compile(r"[^a-z0-9+.#]+")


def tokenize(text: str) -> list[str]:
    tokens = _TOKEN_RE.split(text.lower())
    return [t for t in tokens if len(t) > 1 and t not in _STOPWORDS]


def cosine_similarity(a: list[str], b: list[str]) -> float:
    ca, cb = Counter(a), Counter(b)
    if not ca or not cb:
        return 0.0
    intersection = sum((ca & cb).values())
    denominator = (sum(ca.values()) ** 0.5) * (sum(cb.values()) ** 0.5)
    if denominator == 0:
        return 0.0
    return intersection / denominator


def semantic_similarity(resume_text: str, job_description: str) -> int:
    """Return a similarity score 0-100 between resume and JD text."""
    similarity = cosine_similarity(tokenize(resume_text), tokenize(job_description))
    return max(0, min(100, round(similarity * 100)))