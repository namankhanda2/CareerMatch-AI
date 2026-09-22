import json

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import storage
from app.analyzer import analyze_resume
from app.ats import ats_report
from app.config import settings
from app.jd_parser import parse_job_description
from app.matcher import match_resume
from app.pdf_extractor import extract_text_from_pdf
from app.schemas import AnalysisResult, CompareResponse, ErrorResponse, HistoryList
from app.semantic import semantic_similarity

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_JOB_DESCRIPTION_CHARS = 12_000

app = FastAPI(
    title="CareerMatch AI",
    description="Match a resume PDF against job descriptions.",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    missing = [err.get("loc", [None])[-1] for err in exc.errors() if err.get("type") == "missing"]
    if "resume" in missing and "job_description" in missing:
        message = "Please upload a PDF resume and paste a job description."
    elif "resume" in missing:
        message = "Please upload a PDF resume."
    elif "job_description" in missing:
        message = "Please paste a job description."
    else:
        message = "Invalid request. Check the resume file and job description."
    return JSONResponse(status_code=400, content={"detail": message})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, __: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred. Please try again."},
    )


def _read_uploaded_resume(resume: UploadFile) -> bytes:
    """Validate the uploaded resume and return its bytes. Raises 400 on problems."""
    filename = (resume.filename or "").lower()
    content_type = (resume.content_type or "").lower()
    if not filename.endswith(".pdf") and content_type not in {"application/pdf", "application/x-pdf"}:
        raise HTTPException(status_code=400, detail="Please upload a PDF resume.")

    file_bytes = (resume.file.read() if hasattr(resume, "file") else b"") or b""
    if len(file_bytes) > MAX_FILE_BYTES:
        raise HTTPException(status_code=400, detail="Resume must be 5 MB or smaller.")
    return file_bytes


def _persist_history(source: str, role: str, payload: dict, job_description: str = "") -> None:
    try:
        storage.save_analysis(
            payload,
            source=source,
            role=role,
            job_description=job_description,
        )
    except Exception:
        # History is best-effort; never fail a request because of DB logging.
        pass


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/history", response_model=HistoryList)
def history(limit: int = 50) -> HistoryList:
    return HistoryList(items=storage.list_analyses(limit))


@app.post(
    "/api/analyze",
    response_model=AnalysisResult,
    responses={400: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
async def analyze(
    job_description: str = Form(...),
    resume: UploadFile = File(...),
) -> AnalysisResult:
    job_description = (job_description or "").strip()
    if not job_description:
        raise HTTPException(status_code=400, detail="Please paste a job description.")
    if len(job_description) > MAX_JOB_DESCRIPTION_CHARS:
        raise HTTPException(
            status_code=400,
            detail="Job description is too long. Please keep it under 12,000 characters.",
        )

    resume_text = extract_text_from_pdf(_read_uploaded_resume(resume))

    jd = parse_job_description(job_description)
    match = match_resume(resume_text, jd)
    ats = ats_report(resume_text)
    semantic_score = semantic_similarity(resume_text, job_description)

    result = analyze_resume(resume_text, job_description, match, ats, semantic_score)

    _persist_history("analyze", jd.role, result.model_dump(), job_description)
    return result


@app.post("/api/compare", response_model=CompareResponse)
async def compare(
    job_descriptions: str = Form(...),
    resume: UploadFile = File(...),
) -> CompareResponse:
    try:
        jd_list = json.loads(job_descriptions)
    except (json.JSONDecodeError, TypeError) as exc:
        raise HTTPException(
            status_code=400,
            detail="job_descriptions must be a JSON array of strings.",
        ) from exc
    if (
        not isinstance(jd_list, list)
        or not jd_list
        or not all(isinstance(item, str) for item in jd_list)
    ):
        raise HTTPException(
            status_code=400,
            detail="job_descriptions must be a non-empty JSON array of strings.",
        )

    resume_text = extract_text_from_pdf(_read_uploaded_resume(resume))

    results = []
    ats = ats_report(resume_text)
    for index, jd_text in enumerate(jd_list):
        jd_text = (jd_text or "").strip()
        if not jd_text:
            continue
        jd = parse_job_description(jd_text)
        match = match_resume(resume_text, jd)
        sem = semantic_similarity(resume_text, jd_text)
        results.append(
            {
                "index": index,
                "role": jd.role,
                "title_keywords": jd.title_keywords,
                "match_score": match.match_score,
                "semantic_score": sem,
                "matched_required": match.matched_required,
                "missing_required": match.missing_required,
                "missing_preferred": match.missing_preferred,
                "explanation": match.explanation,
            }
        )
        _persist_history(
            "compare",
            jd.role,
            {
                "match_score": match.match_score,
                "matching_skills": match.matched_skills,
                "missing_skills": match.missing_skills,
                "missing_required_skills": match.missing_required,
                "missing_preferred_skills": match.missing_preferred,
                "strengths": match.strengths,
                "gaps": match.gaps,
                "resume_evidence": match.resume_evidence,
                "explanation": match.explanation,
                "ats": ats,
                "semantic_score": sem,
                "suggestions": [],
                "interview_questions": [],
            },
            jd_text,
        )

    if not results:
        raise HTTPException(status_code=400, detail="No valid job descriptions provided.")
    return CompareResponse(count=len(results), results=results)