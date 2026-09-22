import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _tmp_history_db(monkeypatch, tmp_path):
    """Keep SQLite history isolated to a temp file for every test."""
    from app import storage

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "history.db")


def build_pdf(text: str) -> bytes:
    """Build a small, valid, text-based PDF that pypdf can parse."""
    escaped = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
    stream = f"BT /F1 12 Tf 72 712 Td ({escaped}) Tj ET"
    content = f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream"

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        content.encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num, obj in enumerate(objects, start=1):
        offsets[num] = len(out)
        out += f"{num} 0 obj\n".encode()
        out += obj + b"\n"
        out += b"endobj\n"

    xref_pos = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for num in range(1, len(objects) + 1):
        out += f"{offsets[num]:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    ).encode()
    return bytes(out)


@pytest.fixture(scope="session")
def make_pdf():
    return build_pdf