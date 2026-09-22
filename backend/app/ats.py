"""Deterministic ATS-friendliness report.

Checks what a default ATS parser would be able to pull out of the resume:
recognized sections, length, and contact info. Purely regex-based; no LLM.
"""

import re

from app.parser import split_resume_sections

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_WORD_RE = re.compile(r"[A-Za-z']+")

_BASE_SCORE = 40
_SECTION_POINTS = 10  # education / experience / projects / skills
_SCORE_CAP = 100


def ats_report(resume_text: str) -> dict:
    sections = split_resume_sections(resume_text)
    present: list[str] = []
    if sections.summary.strip():
        present.append("summary")
    if sections.education:
        present.append("education")
    if sections.experience:
        present.append("experience")
    if sections.projects:
        present.append("projects")
    if sections.skills:
        present.append("skills")
    if sections.certifications:
        present.append("certifications")

    word_count = len(_WORD_RE.findall(resume_text))
    has_email = bool(_EMAIL_RE.search(resume_text))

    score = _BASE_SCORE
    for key in ("education", "experience", "projects", "skills"):
        if key in present:
            score += _SECTION_POINTS
    if sections.summary.strip():
        score += _SECTION_POINTS
    if 150 <= word_count <= 1200:
        score += _SECTION_POINTS
    if has_email:
        score += _SECTION_POINTS
    score = min(_SCORE_CAP, score)

    issues: list[str] = []
    if "summary" not in present:
        issues.append("No summary or objective section found.")
    if "experience" not in present:
        issues.append("No work experience section found.")
    if "skills" not in present:
        issues.append("No dedicated skills section found.")
    if word_count < 150:
        issues.append("Resume is short (under 150 words); consider expanding it.")
    if not has_email:
        issues.append("No email address found for recruiters to follow up.")

    return {"score": score, "sections": present, "issues": issues}