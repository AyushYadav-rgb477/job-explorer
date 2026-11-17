"""Extract plain text from an uploaded CV (PDF or DOCX), entirely in memory."""
from __future__ import annotations

import io

from docx import Document
from pypdf import PdfReader

ALLOWED_EXTENSIONS = {"pdf", "docx"}


class CVError(ValueError):
    """The upload can't be read as a CV; the message is safe to show the user."""


def extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def extract_text(filename: str, data: bytes) -> str:
    ext = extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise CVError("Please upload a PDF or DOCX file.")
    try:
        if ext == "pdf":
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            doc = Document(io.BytesIO(data))
            parts = [p.text for p in doc.paragraphs]
            parts += [cell.text for table in doc.tables for row in table.rows for cell in row.cells]
            text = "\n".join(parts)
    except Exception as exc:  # corrupt or password-protected files
        raise CVError("That file couldn't be read. Is it a valid, unlocked PDF/DOCX?") from exc
    if not text.strip():
        raise CVError("No text found in the CV. Scanned (image-only) PDFs aren't supported.")
    return text
