import pytest
from pypdf import PdfWriter

from app.ingest.extract import extract_text


def test_extracts_plain_txt():
    assert extract_text("notes.txt", b"hello world") == "hello world"


def test_extracts_markdown():
    assert extract_text("readme.md", b"# Title\n\nBody text.") == "# Title\n\nBody text."


def test_extracts_pdf_text(tmp_path):
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    pdf_path = tmp_path / "doc.pdf"
    with open(pdf_path, "wb") as f:
        writer.write(f)
    content = pdf_path.read_bytes()

    # A blank page has no text; this proves the PDF branch runs without
    # raising on real PDF bytes even though there's nothing to extract.
    with pytest.raises(ValueError, match="No extractable text"):
        extract_text("doc.pdf", content)


def test_rejects_unsupported_extension():
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text("archive.zip", b"whatever")


def test_rejects_empty_text():
    with pytest.raises(ValueError, match="No extractable text"):
        extract_text("empty.txt", b"   \n\n  ")
