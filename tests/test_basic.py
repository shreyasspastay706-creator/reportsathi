"""
Unit tests for ReportSathi basic functionality.
Tests PyMuPDF text extraction, scanned PDF fallback, file validation, and JSON parsing/fallback.
DOES NOT require an API key or network access.
"""

import pytest
import fitz  # PyMuPDF
from extractor import extract_from_pdf, validate_upload, ExtractionError
from analyzer import clean_and_parse_json


def create_sample_pdf(text: str) -> bytes:
    """Helper to generate an in-memory PDF with specified text."""
    doc = fitz.open()
    page = doc.new_page()
    # Insert text at top of page
    page.insert_text(fitz.Point(50, 72), text, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_pdf_text_extraction():
    """Test standard digital PDF text extraction."""
    sample_text = (
        "COMPLETE BLOOD COUNT (CBC)\n"
        "Hemoglobin: 9.8 g/dL (Reference Range: 12.0 - 15.5)\n"
        "WBC Count: 7,500 /cumm (Reference Range: 4,000 - 11,000)\n"
        "Platelet Count: 250,000 /cumm (Reference Range: 150,000 - 450,000)"
    )
    pdf_bytes = create_sample_pdf(sample_text)

    result = extract_from_pdf(pdf_bytes)
    assert result["mode"] == "text_pdf"
    assert "Hemoglobin" in result["text"]
    assert "9.8" in result["text"]
    assert len(result["images"]) == 0
    assert result["pages_processed"] == 1


def test_scanned_pdf_rendering_fallback():
    """Test that a PDF with less than 50 characters of text triggers scanned mode."""
    # Under 50 characters
    short_text = "CBC Lab"
    pdf_bytes = create_sample_pdf(short_text)

    result = extract_from_pdf(pdf_bytes)
    assert result["mode"] == "scanned_pdf"
    assert len(result["images"]) >= 1
    # Check that image bytes are non-empty PNG
    assert result["images"][0].startswith(b"\x89PNG")


def test_file_validation():
    """Test file size and format validation."""
    # Empty file
    with pytest.raises(ExtractionError, match="uploaded file is empty"):
        validate_upload(b"", "report.pdf")

    # Exceeding 10 MB
    oversized = b"0" * (10 * 1024 * 1024 + 1)
    with pytest.raises(ExtractionError, match="exceeds the maximum allowed limit"):
        validate_upload(oversized, "report.pdf")

    # Unsupported format
    with pytest.raises(ExtractionError, match="Unsupported file format"):
        validate_upload(b"some content", "report.docx")

    # Valid format
    ext = validate_upload(b"valid", "report.PDF")
    assert ext == ".pdf"


def test_json_parsing_success():
    """Test safe parsing of valid JSON output from LLM."""
    sample_json = """
    {
      "is_lab_report": true,
      "readable": true,
      "report_date": "2026-05-10",
      "results": [
        {
          "test": "Hemoglobin",
          "value": "9.8",
          "unit": "g/dL",
          "reference_range": "12.0 - 15.5",
          "flag": "low",
          "explanation": "Measures oxygen-carrying protein in red blood cells.",
          "what_it_may_mean": "A lower value can sometimes be associated with anemia."
        }
      ],
      "urgent_attention": false,
      "urgent_reason": null,
      "questions_for_doctor": [
        "Could my lower hemoglobin level be causing my fatigue?",
        "Do I need any dietary changes or iron evaluation?",
        "When should I repeat this blood test?"
      ],
      "summary": "Your hemoglobin level is slightly below the printed reference range. The other blood counts are within standard ranges. Please review this with your doctor."
    }
    """
    parsed, err = clean_and_parse_json(sample_json)
    assert err is None
    assert parsed is not None
    assert parsed["is_lab_report"] is True
    assert len(parsed["results"]) == 1
    assert parsed["results"][0]["flag"] == "low"
    assert len(parsed["questions_for_doctor"]) == 3


def test_json_parsing_with_code_fences():
    """Test parsing when LLM wraps output in ```json markdown fences."""
    fenced_json = """
    ```json
    {
      "is_lab_report": true,
      "readable": true,
      "report_date": null,
      "results": [],
      "urgent_attention": false,
      "urgent_reason": null,
      "questions_for_doctor": ["What does this mean?"],
      "summary": "All tests look clear."
    }
    ```
    """
    parsed, err = clean_and_parse_json(fenced_json)
    assert err is None
    assert parsed is not None
    assert parsed["summary"] == "All tests look clear."


def test_json_parsing_invalid():
    """Test that malformed JSON returns an error rather than raising an uncaught exception."""
    malformed = "This is not json at all."
    parsed, err = clean_and_parse_json(malformed)
    assert parsed is None
    assert "JSON parsing error" in err
