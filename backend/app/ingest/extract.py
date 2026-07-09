from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

_SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md"}


def extract_text(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in _SUPPORTED_SUFFIXES:
        raise ValueError(f"Unsupported file type: {suffix or filename}")

    if suffix == ".pdf":
        reader = PdfReader(BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        text = content.decode("utf-8")

    text = text.strip()
    if not text:
        raise ValueError(f"No extractable text in {filename}")
    return text
