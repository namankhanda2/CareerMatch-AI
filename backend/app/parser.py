"""Resume section splitting.

Splits raw resume text into canonical sections and attaches each raw skill
mention to the section where it appeared, so downstream evidence is auditable
instead of "trust me".
"""

import re
from dataclasses import dataclass, field

SECTION_HEADERS = [
    "education", "experience", "work experience", "professional experience",
    "employment", "work history", "projects", "project", "skills",
    "technical skills", "core skills", "professional skills", "technologies",
    "tech stack", "competencies", "certifications", "certification",
    "certificates", "licenses", "interests", "hobbies", "languages", "summary",
    "objective", "profile", "about", "contact", "awards", "publications",
    "volunteer", "references",
]

# Maps every recognized header to its canonical section bucket.
_HEADER_BUCKETS = {
    "summary": "summary", "objective": "summary", "profile": "summary",
    "about": "summary",
    "education": "education",
    "experience": "experience", "work experience": "experience",
    "professional experience": "experience", "employment": "experience",
    "work history": "experience",
    "projects": "projects", "project": "projects",
    "skills": "skills", "technical skills": "skills", "core skills": "skills",
    "professional skills": "skills", "technologies": "skills",
    "tech stack": "skills", "competencies": "skills",
    "certifications": "certifications", "certification": "certifications",
    "certificates": "certifications", "licenses": "certifications",
    "interests": "other", "hobbies": "other", "languages": "other",
    "contact": "other", "awards": "other", "publications": "other",
    "volunteer": "other", "references": "other",
}

_HEADER_RE = re.compile(
    r"^\s*(?:(?:#{1,6})\s+)?([A-Za-z][A-Za-z &'/-]{1,40})\s*:?\s*$",
    re.MULTILINE,
)


def _header_names_in_order(text: str) -> list[str]:
    """Return recognized section header names in order of appearance."""
    names: list[str] = []
    for m in _HEADER_RE.finditer(text):
        name = m.group(1).strip().lower()
        if name in SECTION_HEADERS:
            names.append(name)
    return names


@dataclass
class ResumeSections:
    summary: str = ""
    education: list[str] = field(default_factory=list)
    experience: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    other: list[str] = field(default_factory=list)

    def all_text(self) -> str:
        blocks = [
            self.summary,
            *self.education,
            *self.experience,
            *self.projects,
            *self.skills,
            *self.certifications,
            *self.other,
        ]
        return "\n".join(b for b in blocks if b)


def _header_bucket(name: str) -> str:
    return _HEADER_BUCKETS.get(name, "other")


def split_resume_sections(text: str) -> ResumeSections:
    """Split raw resume text into canonical sections.

    Strategy:
      1. Find recognized section headers with _HEADER_RE.
      2. Slice the text between consecutive headers.
      3. Assign each slice to its canonical bucket (synonyms like "work
         experience" or "core skills" map to the same bucket).
      4. Anything before the first header is summary.
    Unrecognized headers land in `other` so nothing is silently dropped.
    """
    headers = _header_names_in_order(text)
    buckets: dict[str, list[str]] = {
        "summary": [], "education": [], "experience": [], "projects": [],
        "skills": [], "certifications": [], "other": [],
    }

    if not headers:
        other: list[str] = []
        for line in text.splitlines():
            if line.strip():
                other.append(line.strip())
        return ResumeSections(other=other)

    current: str = _header_bucket(headers[0])
    started = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        low_line = stripped.lower()
        if low_line in SECTION_HEADERS:
            started = True
            current = _header_bucket(low_line)
            continue
        if started:
            buckets[current].append(stripped)

    summary_lines = _lines_before_first_header(text, headers[0])

    return ResumeSections(
        summary="\n".join(summary_lines),
        education=buckets["education"],
        experience=buckets["experience"],
        projects=buckets["projects"],
        skills=buckets["skills"],
        certifications=buckets["certifications"],
        other=buckets["other"],
    )


def _lines_before_first_header(text: str, first_header: str) -> list[str]:
    idx = text.lower().find(first_header)
    if idx == -1:
        return [s for s in text.splitlines() if s.strip()]
    return [s.strip() for s in text[:idx].splitlines() if s.strip()]
