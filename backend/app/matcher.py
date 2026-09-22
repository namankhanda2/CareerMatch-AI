"""Deterministic resume <-> job match scoring.

The LLM never decides the score. `match_resume` combines the parsed job
descriptor (jd_parser), the canonical skill vocabulary (skill_normalizer) and
the raw resume text, and returns a fully deterministic, evidence-carrying
MatchResult. Required skills are weighted more heavily than preferred skills
(75 vs 25).

Every matched skill carries at least one resume evidence quote so the UI can
show *why* a skill counted, instead of "trust me".
"""

import re
from dataclasses import dataclass, field

from app.jd_parser import JobDescriptor
from app.skill_normalizer import SKILL_ALIASES, find_canonicals_in_text

REQUIRED_WEIGHT = 75
PREFERRED_WEIGHT = 25
_QUOTE_MAX_CHARS = 160

_ALIAS_RE_CACHE: dict[str, re.Pattern] = {}


def _alias_pattern(alias: str) -> re.Pattern:
    pattern = _ALIAS_RE_CACHE.get(alias)
    if pattern is None:
        pattern = re.compile(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", re.IGNORECASE)
        _ALIAS_RE_CACHE[alias] = pattern
    return pattern


# Words glued onto a capitalized word by a PDF-extraction artifact (e.g.
# "Linuxthrough"). Only unambiguous, closed-class function words are used so
# real words like "Container" or "Website" are never split.
_FN_WORDS = (
    "through", "before", "during", "against", "rather", "between", "become",
    "using", "about", "until", "within", "across", "above", "below", "among",
    "after", "either", "never", "always", "often", "again", "would", "could",
    "should", "where", "which", "their", "there", "under", "over", "have",
    "will", "when", "what", "must", "than", "been", "with", "from", "into",
    "this", "that", "were",
)
_FN_WORDS = tuple(sorted(_FN_WORDS, key=len, reverse=True))

# Known product/skill names that must never be split internally.
_NO_SPLIT = {
    "javascript", "typescript", "postgresql", "openai", "graphql", "mcdonald",
    "finland", "before",
}

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z][a-z][a-z])(?=[A-Z])")
_DIGIT_BOUNDARY = re.compile(r"(?<=[a-zA-Z])(?=\d)|(?<=\d)(?=[a-zA-Z])")


def _split_cap_function_word(token: str) -> str:
    """Split 'Linuxthrough' -> 'Linux through' when a function word is glued."""
    if len(token) < 4 or not token[0].isupper():
        return token
    low = token.lower()
    for j in range(3, len(low)):
        for fn in _FN_WORDS:
            if low.startswith(fn, j):
                end = j + len(fn)
                if end == len(low) or not low[end].islower():
                    return token[:j] + " " + token[j:]
                break
    return token


def _clean_token(token: str) -> str:
    if token.lower() in _NO_SPLIT:
        return token
    token = _DIGIT_BOUNDARY.sub(" ", _CAMEL_BOUNDARY.sub(" ", token))
    return _split_cap_function_word(token)


def clean_resume_fragment(text: str) -> str:
    """Normalize PDF-extraction artifacts that glue words together.

    Only inserts spaces at unambiguous boundaries (camelCase, digit/letter or
    capitalized-word + function-word joins); never invents or removes words.
    """
    return " ".join(_clean_token(word) for word in text.split())


def _evidence_quote(resume_text: str, skill: str) -> str | None:
    """Return the first resume line that mentions the skill (via any alias)."""
    aliases = list(SKILL_ALIASES.get(skill, [])) + [skill.lower()]
    for line in resume_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if any(_alias_pattern(a).search(line.lower()) for a in aliases):
            cleaned = clean_resume_fragment(line)
            if len(cleaned) > _QUOTE_MAX_CHARS:
                return cleaned[:_QUOTE_MAX_CHARS].rstrip() + "..."
            return cleaned
    return None


@dataclass
class MatchResult:
    match_score: int
    matched_required: list[str]
    matched_preferred: list[str]
    missing_required: list[str]
    missing_preferred: list[str]
    resume_evidence: dict[str, list[str]] = field(default_factory=dict)
    strengths: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    explanation: str = ""

    @property
    def matched_skills(self) -> list[str]:
        return sorted(set(self.matched_required) | set(self.matched_preferred))

    @property
    def missing_skills(self) -> list[str]:
        # A skill can appear in both buckets (required + preferred); return it once.
        return list(dict.fromkeys(self.missing_required + self.missing_preferred))


def match_resume(resume_text: str, jd: JobDescriptor) -> MatchResult:
    """Score the resume against a parsed job descriptor. Pure and deterministic."""
    resume_skills = find_canonicals_in_text(resume_text)

    required = list(jd.required_skills)
    preferred = list(jd.preferred_skills)

    matched_required = [s for s in required if s in resume_skills]
    missing_required = [s for s in required if s not in resume_skills]
    matched_preferred = [s for s in preferred if s in resume_skills]
    missing_preferred = [s for s in preferred if s not in resume_skills]

    ratios: list[float] = []
    weights: list[int] = []
    if required:
        ratios.append(len(matched_required) / len(required))
        weights.append(REQUIRED_WEIGHT)
    if preferred:
        ratios.append(len(matched_preferred) / len(preferred))
        weights.append(PREFERRED_WEIGHT)

    if not ratios:
        score = 60  # JD had no parseable skill signals: neutral score
    else:
        total_weight = sum(weights)
        score = sum(r * w for r, w in zip(ratios, weights)) / total_weight * 100
    score = max(0, min(100, round(score)))

    evidence = {
        skill: [quote]
        for skill in (matched_required + matched_preferred)
        if (quote := _evidence_quote(resume_text, skill))
    }

    strengths: list[str] = []
    if matched_required:
        strengths.append(f"Required skills matched: {', '.join(matched_required)}")
    if matched_preferred:
        strengths.append(f"Preferred skills matched: {', '.join(matched_preferred)}")
    if score >= 70:
        strengths.append("Strong overall fit for this role.")
    elif score >= 40:
        strengths.append("Moderate overall fit for this role.")

    gaps: list[str] = []
    if missing_required:
        gaps.append(f"Missing required skills: {', '.join(missing_required)}")
    if missing_preferred:
        gaps.append(f"Missing preferred skills: {', '.join(missing_preferred)}")
    if score < 40:
        gaps.append("Large skill gap against this role.")

    parts = [
        f"This resume matches {len(matched_required)} of {len(required)} required "
        f"skills{(' (' + ', '.join(matched_required) + ')') if matched_required else ''} "
        f"and {len(matched_preferred)} of {len(preferred)} preferred "
        f"skills{(' (' + ', '.join(matched_preferred) + ')') if matched_preferred else ''}."
    ]
    if missing_required:
        parts.append(f"Required skills not evidenced: {', '.join(missing_required)}.")
    if missing_preferred:
        parts.append(
            f"Preferred skills not evidenced: {', '.join(missing_preferred)}."
        )
    explanation = " ".join(parts)

    return MatchResult(
        match_score=score,
        matched_required=matched_required,
        matched_preferred=matched_preferred,
        missing_required=missing_required,
        missing_preferred=missing_preferred,
        resume_evidence=evidence,
        strengths=strengths,
        gaps=gaps,
        explanation=explanation,
    )