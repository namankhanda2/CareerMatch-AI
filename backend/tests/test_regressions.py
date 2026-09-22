"""Focused regression tests for the three reported issues:

  1. ``missing_skills`` deduplicates skills that appear in both buckets.
  2. Evidence quotes normalize PDF glue-artifacts (``withGit``, ``Linuxthrough``).
  3. ATS section detection recognizes common heading synonyms.
"""

import pytest

from app.ats import ats_report
from app.matcher import MatchResult, clean_resume_fragment
from app.parser import split_resume_sections


def test_missing_skills_dedupes_overlapping_buckets():
    result = MatchResult(
        match_score=50,
        matched_required=[],
        matched_preferred=[],
        missing_required=["SQL", "Docker"],
        missing_preferred=["SQL", "React"],
    )
    assert result.missing_skills == ["SQL", "Docker", "React"]


def test_missing_skills_keeps_unique_order_without_overlap():
    result = MatchResult(
        match_score=50,
        matched_required=[],
        matched_preferred=[],
        missing_required=["Python", "Docker"],
        missing_preferred=[],
    )
    assert result.missing_skills == ["Python", "Docker"]


def test_clean_normalizes_glue_artifacts():
    assert clean_resume_fragment("Built withGit Linuxthrough and developingREST APIs") == (
        "Built with Git Linux through and developing REST APIs"
    )
    assert clean_resume_fragment("3years Python3 experience") == (
        "3 years Python 3 experience"
    )


def test_clean_never_splits_real_words():
    for word in ["Website", "Mobile", "Python", "Android", "McDonald", "JavaScript", "PostgreSQL"]:
        assert clean_resume_fragment(word) == word


@pytest.mark.parametrize(
    "header", ["experience", "work experience", "professional experience"]
)
def test_ats_detects_experience_synonyms(header):
    text = (
        "jane@example.com\n\n"
        "Summary\nSoftware engineer.\n\n"
        f"{header.title()}\n"
        "Built microservices at Acme.\n"
    )
    sections = split_resume_sections(text)
    assert sections.experience == ["Built microservices at Acme."]
    assert "experience" in ats_report(text)["sections"]


@pytest.mark.parametrize(
    "header", ["skills", "technical skills", "core skills", "professional skills"]
)
def test_ats_detects_skills_synonyms(header):
    text = (
        "jane@example.com\n\n"
        "Summary\nSoftware engineer.\n\n"
        f"{header.title()}\n"
        "Python, FastAPI, Docker\n"
    )
    sections = split_resume_sections(text)
    assert sections.skills == ["Python, FastAPI, Docker"]
    assert "skills" in ats_report(text)["sections"]


def test_ats_report_highlights_previously_dropped_sections():
    text = (
        "jane@example.com\n\n"
        "Work Experience\n"
        "Senior Engineer at Acme.\n"
        "Core Skills\n"
        "Python, FastAPI, Docker\n"
        "certifications\n"
        "AWS Certified Developer\n"
    )
    report = ats_report(text)
    assert {"experience", "skills", "certifications"} <= set(report["sections"])
    assert "No work experience section found." not in report["issues"]
    assert "No dedicated skills section found." not in report["issues"]