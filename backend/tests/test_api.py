import json

import app.analyzer as analyzer_module
from app.jd_parser import parse_job_description
from app.matcher import match_resume
from app.pdf_extractor import extract_text_from_pdf

LLM_PAYLOAD = {
    "suggestions": ["Add a quantified backend project."],
    "interview_questions": [
        "Walk me through a production API you shipped.",
        "How would you design rate limiting?",
        "Describe a debugging incident you owned.",
        "How do you test FastAPI services?",
        "What would you learn first for this role?",
    ],
    "explanation": "The candidate fits well on backend fundamentals but lacks containerization.",
}


class _FakeCompletion:
    def __init__(self, content: str):
        self.choices = [_FakeChoice(content)]


class _FakeChoice:
    def __init__(self, content: str):
        self.message = _FakeMessage(content)


class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class FakeGroq:
    """Minimal stand-in for the Groq client; records the call but never hits the network."""

    def __init__(self, api_key=None, model=None, payload=LLM_PAYLOAD):
        self.api_key = api_key
        self.model = model
        self.payload = payload
        self.chat = _Chat(self)

    def create(self, **kwargs):
        return _FakeCompletion(json.dumps(self.payload))


class _Chat:
    def __init__(self, parent):
        self.completions = _Completions(parent)


class _Completions:
    def __init__(self, parent):
        self.parent = parent

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return self.parent.create(**kwargs)


def _post_analyze(client, resume: bytes, filename: str, job_description: str):
    return client.post(
        "/api/analyze",
        files={"resume": (filename, resume, "application/pdf")},
        data={"job_description": job_description},
    )


def _resume_text(resume: bytes) -> str:
    return extract_text_from_pdf(resume)


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_valid_resume_and_job_description(client, make_pdf, monkeypatch):
    resume = make_pdf(
        "Python engineer.\nEXPERIENCE\nBuilt FastAPI services at scale.\n"
        "SKILLS\nPython, FastAPI, Docker, React"
    )
    jd = "Senior Backend Engineer. Required: Python, FastAPI, Docker. Preferred: React."
    monkeypatch.setattr(analyzer_module.settings, "groq_api_key", "test-key")
    monkeypatch.setattr(analyzer_module, "Groq", FakeGroq)

    response = _post_analyze(client, resume, "resume.pdf", jd)

    assert response.status_code == 200
    body = response.json()

    expected = match_resume(_resume_text(resume), parse_job_description(jd))
    assert body["match_score"] == expected.match_score
    assert 0 <= body["match_score"] <= 100
    assert body["matching_skills"] == expected.matched_skills
    assert body["missing_required_skills"] == expected.missing_required
    assert body["missing_preferred_skills"] == expected.missing_preferred
    assert body["strengths"]
    assert body["resume_evidence"]
    assert body["explanation"] == LLM_PAYLOAD["explanation"]
    assert body["ats"]["score"] > 0
    assert 0 <= body["semantic_score"] <= 100
    assert body["suggestions"] == LLM_PAYLOAD["suggestions"]
    assert len(body["interview_questions"]) == 5


def test_analyze_score_never_comes_from_llm(client, make_pdf, monkeypatch):
    """LlM returns a bogus score, but the response must use the deterministic one."""
    resume = make_pdf("Python engineer. SKILLS: Python, FastAPI. EXPERIENCE: Built services.")
    jd = "Required: Python, FastAPI, Kubernetes. Preferred: Docker, AWS."

    bogus_score = 1  # what the LLM "claims" — must be ignored
    payload = dict(LLM_PAYLOAD, match_score=bogus_score)
    monkeypatch.setattr(analyzer_module.settings, "groq_api_key", "test-key")
    monkeypatch.setattr(
        analyzer_module,
        "Groq",
        lambda api_key=None, model=None, _pl=payload: FakeGroq(
            api_key=api_key, model=model, payload=_pl
        ),
    )

    response = _post_analyze(client, resume, "resume.pdf", jd)
    body = response.json()

    expected = match_resume(_resume_text(resume), parse_job_description(jd))
    assert body["match_score"] == expected.match_score
    assert body["match_score"] != bogus_score


def test_analyze_missing_api_key(client, make_pdf, monkeypatch):
    resume = make_pdf("Python engineer. Built FastAPI services at scale.")
    monkeypatch.setattr(analyzer_module.settings, "groq_api_key", "")

    response = _post_analyze(client, resume, "resume.pdf", "Python developer role.")

    assert response.status_code == 500
    assert "GROQ_API_KEY" in response.json()["detail"]


def test_analyze_invalid_pdf(client):
    response = _post_analyze(client, b"this is not a pdf", "resume.pdf", "Python role.")

    assert response.status_code == 400
    assert response.json()["detail"]


def test_analyze_oversized_pdf(client):
    oversized = b"x" * (5 * 1024 * 1024 + 1)
    response = _post_analyze(client, oversized, "resume.pdf", "Python role.")

    assert response.status_code == 400
    assert "5 MB" in response.json()["detail"]


def test_analyze_empty_file(client):
    response = _post_analyze(client, b"", "resume.pdf", "Python role.")

    assert response.status_code == 400


def test_analyze_empty_job_description(client, make_pdf):
    resume = make_pdf("Python engineer.")
    response = _post_analyze(client, resume, "resume.pdf", "   ")

    assert response.status_code == 400
    assert "job description" in response.json()["detail"].lower()


def test_analyze_missing_job_description_field(client, make_pdf):
    resume = make_pdf("Python engineer.")
    response = client.post(
        "/api/analyze",
        files={"resume": ("resume.pdf", resume, "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["detail"]


def test_analyze_missing_resume_field(client):
    response = client.post("/api/analyze", data={"job_description": "Python role."})

    assert response.status_code == 400
    assert response.json()["detail"]


def test_analyze_non_pdf_file_type(client):
    response = client.post(
        "/api/analyze",
        files={"resume": ("notes.txt", b"hello", "text/plain")},
        data={"job_description": "Python role."},
    )

    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


def test_compare_multiple_job_descriptions(client, make_pdf, monkeypatch):
    resume = make_pdf(
        "Python engineer. SKILLS: Python, FastAPI. EXPERIENCE: Built FastAPI services."
    )
    jds = [
        "Backend Developer. Required: Python, FastAPI.",
        "Frontend Developer. Required: React, TypeScript. Preferred: Python.",
        "DevOps Engineer. Required: Docker, Kubernetes, AWS.",
    ]
    response = client.post(
        "/api/compare",
        files={"resume": ("resume.pdf", resume, "application/pdf")},
        data={"job_descriptions": json.dumps(jds)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 3
    assert len(body["results"]) == 3

    scores = [r["match_score"] for r in body["results"]]
    roles = [r["role"] for r in body["results"]]
    assert all(0 <= s <= 100 for s in scores)
    assert scores[0] > scores[1]  # same-stack backend role beats frontend role
    assert any("devops" in role.lower() for role in roles)
    devops = next(r for r in body["results"] if "devops" in r["role"].lower())
    assert devops["missing_required"]  # resume has no Docker/Kubernetes/AWS
    assert all(isinstance(r["missing_required"], list) for r in body["results"])


def test_compare_invalid_json(client, make_pdf):
    resume = make_pdf("Python engineer.")
    response = client.post(
        "/api/compare",
        files={"resume": ("resume.pdf", resume, "application/pdf")},
        data={"job_descriptions": "not-json"},
    )

    assert response.status_code == 400
    assert "JSON array" in response.json()["detail"]


def test_history_records_analyzes(client, make_pdf, monkeypatch):
    resume = make_pdf(
        "Python engineer. SKILLS: Python, FastAPI. EXPERIENCE: Built FastAPI services."
    )
    jd = "Required: Python, FastAPI. Preferred: Docker."
    monkeypatch.setattr(analyzer_module.settings, "groq_api_key", "test-key")
    monkeypatch.setattr(analyzer_module, "Groq", FakeGroq)

    analyze_resp = _post_analyze(client, resume, "resume.pdf", jd)
    assert analyze_resp.status_code == 200

    history = client.get("/api/history?limit=10")
    assert history.status_code == 200
    items = history.json()["items"]
    assert len(items) >= 1
    latest = items[0]
    assert latest["source"] == "analyze"
    assert latest["match_score"] == analyze_resp.json()["match_score"]
    assert latest["payload"]["match_score"] == analyze_resp.json()["match_score"]