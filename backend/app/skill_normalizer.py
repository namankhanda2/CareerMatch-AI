"""Canonical skill normalization.

The single source of truth for "these all mean the same skill".
Downstream modules (parser, jd_parser, matcher) depend on this so that
ReactJS, React.js, and react are counted as ONE skill.
"""

import re
from functools import lru_cache

SKILL_ALIASES: dict[str, list[str]] = {
    "React": ["react", "reactjs", "react.js", "react js"],
    "JavaScript": ["javascript", "js", "es6", "ecmascript"],
    "TypeScript": ["typescript", "ts"],
    "Node.js": ["nodejs", "node", "node.js"],
    "Python": ["python"],
    "FastAPI": ["fastapi"],
    "Django": ["django"],
    "SQL": ["sql", "sqlite", "mysql", "postgresql", "postgres"],
    "Docker": ["docker"],
    "Kubernetes": ["kubernetes", "k8s"],
    "AWS": ["aws", "amazon web services"],
    "Git": ["git", "github", "gitlab"],
    "REST API": ["rest api", "restful api", "rest", "restful"],
    "Machine Learning": ["machine learning", "ml"],
    "Deep Learning": ["deep learning", "dl"],
}

_ALIAS_TO_CANONICAL: dict[str, str] = {}
for _canonical, _aliases in SKILL_ALIASES.items():
    for _alias in _aliases:
        _ALIAS_TO_CANONICAL[_alias] = _canonical

_PATTERN_CACHE: dict[str, re.Pattern] = {}


def _escape(alias: str) -> re.Pattern:
    if alias not in _PATTERN_CACHE:
        _PATTERN_CACHE[alias] = re.compile(
            rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])"
        )
    return _PATTERN_CACHE[alias]


@lru_cache(maxsize=4096)
def normalize_skill(raw: str) -> str:
    """Return the canonical name for a skill alias."""
    key = raw.strip().lower().replace("_", " ").strip()
    if key in _ALIAS_TO_CANONICAL:
        return _ALIAS_TO_CANONICAL[key]
    return raw.strip()


def find_canonicals_in_text(text: str) -> set[str]:
    """Return canonical skills whose aliases appear in `text`.

    Word-boundary aware: "js" never matches inside "json"; "react" never
    matches inside "reactnative".
    """
    found: set[str] = set()
    low = text.lower()
    for alias, canonical in _ALIAS_TO_CANONICAL.items():
        if _escape(alias).search(low):
            found.add(canonical)
    return found
