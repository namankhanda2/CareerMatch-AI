# CareerMatch AI

Match a PDF resume against a job description. The app extracts the resume
text, scores the fit with a Groq-powered LLM, and shows a clear analysis:
match score, matching skills, missing skills, improvement suggestions, and
five tailored interview questions.

## Features

- PDF resume upload with drag-and-drop, size, and type validation
- Uses Groq's fast LLM API for structured JSON analysis
- Returns a 0–100 match score with a visual gauge
- Lists matching and missing skills as pills
- Provides concrete resume-improvement suggestions
- Generates five role-specific interview questions
- Clean, responsive Tailwind UI (desktop and mobile)
- No uploads or results are stored anywhere

## Tech stack

| Layer | Technology |
| --- | --- |
| Frontend | React 18, Vite 6, Tailwind CSS 3 |
| Backend | Python 3.11+, FastAPI, pydantic |
| PDF text | pypdf |
| AI | Groq (llama-3.3-70b-versatile) |

## Architecture

```
Browser (React/Vite, :5173)
        │  POST /api/analyze  (multipart/form-data)
        ▼
FastAPI backend (:8000)
   └─ PDF validation + text extraction (pypdf)
   └─ Groq LLM call → structured JSON
   └─ Response validation (pydantic)
        ▼
Structured analysis → Results UI
```

In development, Vite proxies `/api` requests to `http://127.0.0.1:8000`, so no
CORS configuration is needed and the Groq API key never leaves the backend.

## Folder structure

```
CareerMatch-AI/
├── .env.example              # Template for backend/.env
├── .gitignore
├── README.md
├── backend/
│   ├── .env                  # Your local secrets (gitignored)
│   ├── requirements.txt      # Runtime dependencies
│   ├── requirements-dev.txt  # Test dependencies
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI app, routes, error handlers
│   │   ├── analyzer.py       # Groq LLM call + response parsing
│   │   ├── config.py         # Environment-backed settings
│   │   ├── pdf_extractor.py  # PDF text extraction
│   │   └── schemas.py        # Pydantic response models
│   └── tests/
│       ├── conftest.py       # TestClient + PDF fixture helpers
│       └── test_api.py       # API tests
└── frontend/
    ├── .env.example          # Optional VITE_API_URL override
    ├── index.html
    ├── package.json
    ├── vite.config.js        # Dev proxy to backend
    └── src/
        ├── main.jsx          # React entry
        ├── App.jsx           # Main UI and form logic
        ├── api.js            # Fetch wrapper for /api/analyze
        ├── index.css         # Tailwind styles
        └── components/
            ├── Results.jsx
            ├── ScoreGauge.jsx
            └── SkillPills.jsx
```

## Environment variables

Create `backend/.env` from the template:

```bash
cp .env.example backend/.env
```

| Variable | Required | Purpose |
| --- | --- | --- |
| `GROQ_API_KEY` | Yes | Groq API key used for analysis |
| `GROQ_MODEL` | No | Defaults to `llama-3.3-70b-versatile` |
| `CORS_ORIGINS` | No | Comma-separated allowed origins (defaults cover local Vite) |

The backend loads these only from environment variables — the API key is never
sent to the frontend. `.env` files are ignored by git.

Optional frontend override: create `frontend/.env` with
`VITE_API_URL=http://127.0.0.1:8000` if you are not using the Vite proxy.

## Prerequisites

- Node.js 18+
- Python 3.11+
- A [Groq API key](https://console.groq.com/keys)

## Local setup

1. Clone or copy the project, then create the backend env file:

   ```bash
   cp .env.example backend/.env
   ```

2. Set your `GROQ_API_KEY` in `backend/.env`.

### Run the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check: http://127.0.0.1:8000/api/health

Interactive docs (Swagger UI): http://127.0.0.1:8000/docs

### Run the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` to the backend.

## API endpoints

### `GET /api/health`

Returns `{ "status": "ok" }`.

### `POST /api/analyze`

`multipart/form-data`

| Field | Type | Required |
| --- | --- | --- |
| `resume` | PDF file | yes |
| `job_description` | string | yes |

Success (`200`):

```json
{
  "match_score": 78,
  "matching_skills": ["Python", "FastAPI"],
  "missing_skills": ["Kubernetes"],
  "suggestions": ["Add a quantified backend project."],
  "interview_questions": [
    "Walk me through a production API you shipped.",
    "How would you design rate limiting?",
    "Describe a debugging incident you owned.",
    "How do you test FastAPI services?",
    "What would you learn first for this role?"
  ]
}
```

Errors return `{ "detail": "..." }` with:

| Status | Meaning |
| --- | --- |
| `400` | Validation problem (missing fields, invalid/empty PDF, oversize, empty job description) |
| `429` | Groq rate limit reached |
| `500` | Server-side misconfiguration (e.g. missing API key) |
| `502` | The model or API returned an invalid/unexpected result |

## Example workflow

1. Open http://localhost:5173.
2. Drag a text-based PDF resume into the upload area (max 5 MB).
3. Paste a job description (max 12,000 characters).
4. Click **Analyze match**.
5. Review the score gauge, skill pills, suggestions, and interview questions.

## Testing

Backend tests use pytest and `fastapi.testclient`. They cover the health
endpoint, PDF validation (invalid, oversized, empty, wrong type), form
validation (missing or empty job description / resume), and an end-to-end
analyze call with the Groq client mocked.

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

## Notes and limitations

- Scanned/image-only PDFs usually have no extractable text and are rejected.
- Password-protected PDFs are rejected.
- Resume text is truncated at 20,000 characters before being sent to the model.
- The app does not store uploads or analysis results.

## Future improvements

- Support DOCX and other resume formats
- OCR fallback for scanned PDFs
- Stream partial results (suggestions arrive as they are generated)
- Persist analysis history and track matches over time
- Add frontend tests (Vitest/Testing Library)
- Dockerize the app for one-command deployment
- Add GitHub Actions CI to run lint, tests, and build on every push