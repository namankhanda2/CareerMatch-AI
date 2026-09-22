"""Job description parsing (deterministic, evidence-carrying).

Brews a job description down into a structured ``JobDescriptor``:

  * required_skills     -> canonical skills mentioned under "required/must"
  * preferred_skills    -> canonical skills mentioned under "preferred/nice-to-have"
  * min_years           -> highest "N years" figure in the text
  * education           -> degree keywords (bachelor/master/phd, ...)
  * responsibilities    -> the raw sentences that carried the required skills
  * title_keywords      -> role words from the first lines (used by history/compare)
  * role                -> short human label for the role (used by history/compare)

Skill extraction is delegated to ``skill_normalizer.find_canonicals_in_text``
so that "React.js", "reactjs" and "React" all collapse to one canonical token —
identical to how the resume parser resolves skills (single source of truth).
No LLM, no network, no API key: every step is plain regex + the alias map.
"""

import re
from dataclasses import dataclass, field

from app.skill_normalizer import find_canonicals_in_text

# Phrases after which sentences are treated as "required" (vs. "preferred").
_REQUIRED_INTRO = re.compile(
    r"\b(?:required|must ?have|essential|minimum qualifications?|"
    r"what you'?ll? need|what we'?re looking for)\b",
    re.IGNORECASE,
)
_PREFERRED_INTRO = re.compile(
    r"\b(?:preferred|nice to have|nice-to-have|a plus|plus|bonus|"
    r"added bonus|desired|nice to-have)\b",
    re.IGNORECASE,
)

_YEARS_RE = re.compile(
    r"(\d{1,2})\s*(?:\+|to\s+\d{1,2}\b)?\s*(?:years?|yrs?)\b", re.IGNORECASE
)
_EDUCATION_RE = re.compile(
    r"\b(bachelor(?:'s| of)?|b\.?s\.?|b\.?a\.?|master(?:'s| of)?|"
    r"m\.?s\.?|m\.?a\.?|phd|doctorate|b\.?e\.?|m\.?e\.?)\b",
    re.IGNORECASE,
)

# Words that never describe the role itself (title line noise / labels).
_ROLE_STOPWORDS = {
    "required", "preferred", "skills", "skill", "job", "role", "position",
    "description", "posting", "career", "opportunity", "we", "are", "seeking",
    "looking", "an", "a", "the", "for", "and", "at", "or", "to", "of", "in",
    "minimum", "qualifications", "requirements", "what", "you", "ll", "need",
    "nice", "have", "to", "plus", "bonus", "backend", "engineer", "developer",
}

# Words that never get treated as role keywords even if they appear in a
# headline (labels like "Senior Backend Engineer - Build REST APIs").
_TITLE_STOPWORDS = {
    "job", "role", "position", "description", "posting", "career", "we", "are",
    "seeking", "looking", "an", "a", "the", "for", "and", "at", "or", "to",
    "of", "in", "build", "create", "develop", "developing", "building",
    "required", "preferred", "skills", "min", "years", "experience",
}


@dataclass
class JobDescriptor:
    """Structured, evidence-carrying view of a job description."""

    title_keywords: list[str] = field(default_factory=list)
    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    min_years: int = 0
    education: list[str] = field(default_factory=list)
    responsibilities: list[str] = field(default_factory=list)
    role: str = ""

    def __bool__(self) -> bool:
        return bool(
            self.required_skills
            or self.preferred_skills
            or self.title_keywords
            or self.responsibilities
        )


def parse_job_description(text: str) -> JobDescriptor:
    """Parse a job description into a ``JobDescriptor``.

    Deterministic and pure: given the same text it always returns the same
    descriptor, so tests can lock against the exact canonically-normalized
    output (skill aliases resolved via skill_normalizer).
    """
    buckets = _buckets_for_intent(text)
    return JobDescriptor(
        title_keywords=_title_keywords(text),
        required_skills=_skills_from(buckets["required"]),
        preferred_skills=_skills_from(buckets["preferred"]),
        min_years=_extract_min_years(text),
        education=_extract_education(text),
        responsibilities=[s for s in buckets["required"] if s.strip()],
        role=_extract_role(text),
    )


def _buckets_for_intent(text: str) -> dict[str, list[str]]:
    """Bucket sentences by intent (required / preferred / neutral).

    Everything before any intro is "neutral" — skills that sit in the opening
    blurb (e.g. "We build React apps") are still found, but the "required"
    responsibility list only records sentences actually bucketed as required.
    """
    sentences = _split_sentences(text)
    buckets: dict[str, list[str]] = {
        "required": [],
        "preferred": [],
        "neutral": [],
    }
    current = "neutral"
    for sentence in sentences:
        low = sentence.lower()
        if _REQUIRED_INTRO.search(low):
            current = "required"
        elif _PREFERRED_INTRO.search(low):
            current = "preferred"
        buckets[current].append(sentence.strip())
    return buckets


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences on punctuation **and** newlines.

    Real job descriptions lay out "Preferred: ..." and "Required: ..." on
    separate lines with no terminal punctuation, so we must treat a newline as
    a boundary too — otherwise the whole block collapses into one sentence and
    the first intro-match ("required") swallows preferred skills like React.
    Decimal/acronym dots ("C++", "B.S.") never split because the boundary only
    triggers after ``.?`` / ``!?`` followed by whitespace.
    """
    pieces: list[str] = []
    for part in text.splitlines():
        part = part.strip()
        if not part:
            continue
        # A newline is a boundary even without terminal punctuation — real JDs
        # lay out "Preferred: React, TypeScript" and "Required: python, sql" on
        # separate lines. Splitting on the line first lets each intro-route its
        # own skills instead of "Required" swallowing preferred React.
        pieces.append(part)
        pieces.extend(
            p.strip()
            for p in re.split(r"(?<=[.!?])\s+", part)
            if p and p.strip()
        )
    return pieces


def _skills_from(sentences: list[str]) -> list[str]:
    """Return canonical skills found across a bucket's sentences (sorted)."""
    hits: set[str] = set()
    for sentence in sentences:
        hits |= find_canonicals_in_text(sentence)
    return sorted(hits)


def _extract_min_years(text: str) -> int:
    """Highest "N years" figure found in the text, else 0."""
    years = [int(m.group(1)) for m in _YEARS_RE.finditer(text)]
    return max(years, default=0)


def _extract_education(text: str) -> list[str]:
    """Degree keywords found (deduplicated, normalized, dot-stripped)."""
    found = []
    for m in _EDUCATION_RE.finditer(text):
        token = m.group(1).lower().replace(".", "")
        if token not in found:
            found.append(token)
    return found


def _extract_role(text: str) -> str:
    """Short human role label, lifted from the headline lines.

    Prefers the first non-empty headline, falling back to the first line that
    is not pure intro noise; returns "" when nothing usable is found.
    """
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        low = line.lower()
        if low in _ROLE_STOPWORDS or all(_is_stopword(t) for t in line.split()):
            continue
        # "Senior Backend Engineer - Build REST APIs" -> "Senior Backend Engineer"
        role = re.split(r"\s+[-–—]\s+", line, maxsplit=1)[0].rstrip(".:")
        role = " ".join(t for t in role.split() if t and t.lower() not in _ROLE_STOPWORDS)
        if role:
            return role.title()
    return ""


def _is_stopword(token: str) -> bool:
    return token.lower() in _ROLE_STOPWORDS


def _title_keywords(text: str) -> list[str]:
    """Role words from the first headline lines (deduped, ordered)."""
    words: list[str] = []
    for idx, line in enumerate(text.splitlines()[:3]):
        line = line.strip()
        if not line:
            continue
        for token in re.split(r"\W+", line):
            low = token.lower()
            if (
                low
                and low not in _TITLE_STOPWORDS
                and len(low) > 1
                and (idx > 0 or low not in _ROLE_STOPWORDS)
            ):
                words.append(low)
    return list(dict.fromkeys(words))
