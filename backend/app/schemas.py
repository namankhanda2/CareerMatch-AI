from pydantic import BaseModel, Field


class AtsReport(BaseModel):
    score: int = Field(..., ge=0, le=100)
    sections: list[str]
    issues: list[str]


class AnalysisResult(BaseModel):
    match_score: int = Field(..., ge=0, le=100)
    matching_skills: list[str]
    missing_skills: list[str]
    missing_required_skills: list[str]
    missing_preferred_skills: list[str]
    strengths: list[str]
    gaps: list[str]
    resume_evidence: dict[str, list[str]]
    explanation: str
    ats: AtsReport
    semantic_score: int = Field(..., ge=0, le=100)
    suggestions: list[str]
    interview_questions: list[str]


class ErrorResponse(BaseModel):
    detail: str


class HistoryItem(BaseModel):
    id: int
    source: str
    timestamp: str
    role: str
    match_score: int
    semantic_score: int
    ats_score: int
    job_description: str = ""
    payload: AnalysisResult


class HistoryList(BaseModel):
    items: list[HistoryItem]


class CompareResult(BaseModel):
    index: int
    role: str = ""
    title_keywords: list[str] = []
    match_score: int = Field(..., ge=0, le=100)
    semantic_score: int = Field(..., ge=0, le=100)
    matched_required: list[str] = []
    missing_required: list[str] = []
    missing_preferred: list[str] = []
    explanation: str = ""


class CompareResponse(BaseModel):
    count: int
    results: list[CompareResult]