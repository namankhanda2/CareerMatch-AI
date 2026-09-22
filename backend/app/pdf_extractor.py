from io import BytesIO

from fastapi import HTTPException
from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_RESUME_CHARS = 20_000


def extract_text_from_pdf(file_bytes: bytes) -> str:
    if not file_bytes:
        raise HTTPException(status_code=400, detail="The uploaded PDF is empty.")

    try:
        reader = PdfReader(BytesIO(file_bytes))
    except (PdfReadError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Could not read the PDF. Please upload a valid, unencrypted resume.",
        ) from exc

    if getattr(reader, "is_encrypted", False):
        raise HTTPException(
            status_code=400,
            detail="This PDF is password-protected. Please upload an unlocked resume.",
        )

    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text.strip())

    combined = "\n\n".join(pages).strip()
    if not combined:
        raise HTTPException(
            status_code=400,
            detail="No readable text was found in the PDF. Try a text-based resume instead of a scanned image.",
        )

    if len(combined) > MAX_RESUME_CHARS:
        combined = combined[:MAX_RESUME_CHARS]

    return combined
