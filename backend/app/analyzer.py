import json
import re

from fastapi import HTTPException
from groq import APIError, AuthenticationError, Groq, RateLimitError

from app.config import settings
from app.matcher import MatchResult
from app.schemas import AnalysisResult, AtsReport

SYSTEM_PROMPT = """You are a precise career coach and recruiter.

A deterministic engine has already parsed the resume and job description and
computed the match score, matched/missing skills, strengths, and gaps. Your
job is to explain that evidence in human terms and give next steps. Never
recalculate or restate the numeric score.

Return ONLY valid JSON with this exact shape:
{
  "suggestions": ["3-6 concrete resume or experience improvements as short sentences"],
  "interview_questions": ["exactly 5 likely interview questions for this role, tailored to the resume gap or strengths"],
  "explanation": "2-3 sentence narrative synthesizing the strengths and gaps"
}

Rules:
- Base everything strictly on the resume and job description provided.
- Do not invent employer names or credentials that are not in the resume.
- Keep skill names concise (1-5 words).
"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise HTTPException(
        status_code=502,
        detail="The analysis model returned an unexpected response. Please try again.",
    )


def analyze_resume(
    resume_text: str,
    job_description: str,
    match: MatchResult,
    ats: dict,
    semantic_score: int,
) -> AnalysisResult:
    if not settings.groq_api_key:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY is not configured. Add it to backend/.env and restart the server.",
        )

    client = Groq(api_key=settings.groq_api_key)
    computed_facts = (
        f"COMPUTED EVIDENCE (ground truth, do not change the score):\n"
        f"- Deterministic match score: {match.match_score}/100\n"
        f"- Matched skills: {', '.join(match.matched_skills) or 'none'}\n"
        f"- Missing required skills: {', '.join(match.missing_required) or 'none'}\n"
        f"- Missing preferred skills: {', '.join(match.missing_preferred) or 'none'}\n"
        f"- Strengths: {'; '.join(match.strengths) or 'none'}\n"
        f"- Gaps: {'; '.join(match.gaps) or 'none'}\n"
    )
    user_prompt = (
        "RESUME:\n"
        f"{resume_text}\n\n"
        "JOB DESCRIPTION:\n"
        f"{job_description}\n\n"
        f"{computed_facts}"
    )

    try:
        response = client.chat.completions.create(
            model=settings.groq_model,
            temperature=0.3,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=502,
            detail="Groq rejected the API key. Check GROQ_API_KEY in backend/.env.",
        ) from exc
    except RateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail="The analysis service is rate-limited. Please wait a moment and try again.",
        ) from exc
    except APIError as exc:
        groq_message = getattr(exc, "message", None) or str(exc)
        raise HTTPException(
            status_code=502,
            detail=f"Groq analysis failed: {groq_message}",
        ) from exc
    except Exception as exc:
        # Last-resort guard: never leak internals or the API key to the client.
        raise HTTPException(
            status_code=502,
            detail="Groq analysis failed unexpectedly. Please try again.",
        ) from exc

    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise HTTPException(
            status_code=502,
            detail="The analysis model returned an empty response. Please try again.",
        )

    payload = _extract_json(content)

    suggestions = payload.get("suggestions") or []
    if not isinstance(suggestions, list):
        suggestions = []
    suggestions = [str(s).strip() for s in suggestions if str(s).strip()][:6]

    questions = payload.get("interview_questions") or []
    if not isinstance(questions, list):
        questions = []
    questions = [str(q).strip() for q in questions if str(q).strip()]
    if len(questions) < 5:
        raise HTTPException(
            status_code=502,
            detail="The analysis was incomplete. Please try again.",
        )

    llm_explanation = str(payload.get("explanation") or "").strip()

    return AnalysisResult(
        match_score=max(0, min(100, int(match.match_score))),
        matching_skills=match.matched_skills,
        missing_skills=match.missing_skills,
        missing_required_skills=match.missing_required,
        missing_preferred_skills=match.missing_preferred,
        strengths=match.strengths,
        gaps=match.gaps,
        resume_evidence=match.resume_evidence,
        explanation=llm_explanation or match.explanation,
        ats=AtsReport(**ats),
        semantic_score=max(0, min(100, int(semantic_score))),
        suggestions=suggestions,
        interview_questions=questions[:5],
    )