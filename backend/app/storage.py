"""SQLite persistence for analysis history.

History is a convenience, not a critical path: every write is wrapped so a DB
problem can never fail a user-facing request. The full analysis payload is
stored as JSON; a few denormalized columns power the list view.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "history.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL DEFAULT 'analyze',
                timestamp TEXT NOT NULL,
                role TEXT,
                match_score INTEGER,
                semantic_score INTEGER,
                ats_score INTEGER,
                job_description TEXT,
                payload TEXT NOT NULL
            )
            """
        )


def save_analysis(
    payload: dict,
    *,
    source: str = "analyze",
    role: str = "",
    job_description: str = "",
) -> dict:
    """Persist an analysis payload; returns the stored record (with id)."""
    _init_db()
    record = {
        "id": None,
        "source": source,
        "timestamp": _now(),
        "role": role,
        "match_score": payload.get("match_score"),
        "semantic_score": payload.get("semantic_score"),
        "ats_score": (payload.get("ats") or {}).get("score"),
        "job_description": job_description,
        "payload": payload,
    }
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO analyses
                (source, timestamp, role, match_score, semantic_score, ats_score,
                 job_description, payload)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["source"],
                record["timestamp"],
                record["role"],
                record["match_score"],
                record["semantic_score"],
                record["ats_score"],
                record["job_description"],
                json.dumps(payload),
            ),
        )
        record["id"] = cur.lastrowid
    return record


def _row_to_record(row: sqlite3.Row) -> dict:
    record = {
        "id": row["id"],
        "source": row["source"],
        "timestamp": row["timestamp"],
        "role": row["role"],
        "match_score": row["match_score"],
        "semantic_score": row["semantic_score"],
        "ats_score": row["ats_score"],
        "job_description": row["job_description"] or "",
    }
    try:
        record["payload"] = json.loads(row["payload"] or "{}")
    except (ValueError, TypeError):
        record["payload"] = {}
    return record


def list_analyses(limit: int = 50) -> list[dict]:
    """Return the most recent analyses, including full payloads (newest first)."""
    _init_db()
    limit = max(1, min(int(limit), 200))
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM analyses ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_row_to_record(row) for row in rows]