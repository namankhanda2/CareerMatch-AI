"""Tests for jd_parser.parse_job_description.

The parser is deterministic (stdlib `re` only — no network, no API key), so
every assertion below reflects what the code actually returns on the input
givenles, not what an LLM "thinks".
"""

from app.jd_parser import parse_job_description


def test_role_extracted_from_title_line():
    jd = "Senior Backend Engineer - Build REST APIs at Acme\n"
    desc = parse_job_description(jd)
    # Role-label contract: title noise words (backend, engineer, developer, ...)
    # are stripped, leaving the core label like "Senior".
    assert "senior" in desc.role.lower()
    assert desc.role


def test_required_skills_header():
    text = (
        "Senior Backend Engineer\n"
        "Required skills: FastAPI, Docker, Kubernetes, PostgreSQL\n"
        "Min 5 years of backend experience.\n"
    )
    desc = parse_job_description(text)
    # Skill-normalization contract: "PostgreSQL" is an alias of the canonical
    # "SQL", so it must appear as the canonical skill.
    assert "sql" in [s.lower() for s in desc.required_skills]
    assert desc.min_years >= 5


def test_preferred_skills_go_to_preferred_bucket():
    text = (
        "Preferred skills: React, TypeScript\n"
        "Required: python, sql\n"
    )
    desc = parse_job_description(text)
    joined = " ".join(desc.required_skills).lower()
    assert "react" not in joined
    pref = " ".join(desc.preferred_skills).lower()
    assert "react" in pref


def test_education_requirement_detected():
    text = "Requires a Bachelor's degree in Computer Science.\n"
    desc = parse_job_description(text)
    assert any("bachelor" in e.lower() for e in desc.education)


def test_min_years_from_range_expression():
    text = "Need 3-5 years of Python experience."
    desc = parse_job_description(text)
    assert desc.min_years >= 3


def test_empty_text_yields_empty_descriptor():
    desc = parse_job_description("")
    assert not desc.required_skills
    assert desc.min_years == 0
    assert not desc.role
