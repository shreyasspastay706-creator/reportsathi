"""
ReportSathi - Document and Image Extractor
Handles validation and PyMuPDF text/image extraction in memory.
"""

from typing import Dict, Any, List
import io
import fitz  # PyMuPDF


class ExtractionError(Exception):
    """Custom exception for user-friendly extraction errors."""
    pass


MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}


def validate_upload(file_bytes: bytes, file_name: str) -> str:
    """
    Validates file size, non-emptiness, and file format.
    Returns normalized file extension.
    """
    if not file_bytes or len(file_bytes) == 0:
        raise ExtractionError("The uploaded file is empty. Please upload a valid medical lab report.")

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        size_mb = len(file_bytes) / (1024 * 1024)
        raise ExtractionError(
            f"File size ({size_mb:.1f} MB) exceeds the maximum allowed limit of 10 MB. "
            "Please upload a smaller file or reduce the image resolution."
        )

    file_name_lower = file_name.lower()
    matched_ext = None
    for ext in ALLOWED_EXTENSIONS:
        if file_name_lower.endswith(ext):
            matched_ext = ext
            break

    if not matched_ext:
        raise ExtractionError(
            "Unsupported file format. Please upload a PDF or an image (JPG, PNG)."
        )

    return matched_ext


def extract_from_pdf(pdf_bytes: bytes, max_pages: int = 5) -> Dict[str, Any]:
    """
    Extracts text from a PDF in-memory using PyMuPDF.
    If extracted text is under 50 characters, renders up to max_pages as PNG images (~150 DPI)
    to be processed by model vision.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        raise ExtractionError("Could not open this PDF. The file may be corrupt or not a valid PDF.") from e

    if doc.is_encrypted:
        raise ExtractionError("This PDF is password-protected. Please remove password protection before uploading.")

    total_pages = len(doc)
    if total_pages == 0:
        raise ExtractionError("The uploaded PDF has no pages.")

    full_text_parts: List[str] = []
    for page_num in range(min(total_pages, max_pages)):
        page = doc[page_num]
        full_text_parts.append(page.get_text())

    combined_text = "\n".join(full_text_parts).strip()

    # If text is under 50 characters, treat as scanned PDF
    if len(combined_text) < 50:
        # Render pages to PNG at ~150 DPI (standard 72 DPI * 150/72 = ~2.0833)
        zoom = 150.0 / 72.0
        mat = fitz.Matrix(zoom, zoom)
        rendered_images: List[bytes] = []

        pages_to_render = min(total_pages, max_pages)
        for page_idx in range(pages_to_render):
            page = doc[page_idx]
            pix = page.get_pixmap(matrix=mat, alpha=False)
            png_bytes = pix.tobytes("png")
            rendered_images.append(png_bytes)

        return {
            "mode": "scanned_pdf",
            "text": combined_text,
            "images": rendered_images,
            "pages_processed": pages_to_render,
            "total_pages": total_pages
        }

    return {
        "mode": "text_pdf",
        "text": combined_text,
        "images": [],
        "pages_processed": min(total_pages, max_pages),
        "total_pages": total_pages
    }


def prepare_image(image_bytes: bytes, ext: str) -> Dict[str, Any]:
    """
    Prepares uploaded image bytes for model vision.
    """
    mime_type = "image/png" if ext == ".png" else "image/jpeg"
    return {
        "mode": "image",
        "mime_type": mime_type,
        "images": [image_bytes],
        "text": ""
    }
