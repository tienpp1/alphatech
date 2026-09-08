"""
Document parsing pipeline for Knowledge Base.
Supports PDF (via pypdf), Word DOCX (via python-docx), and Plain Text/Markdown.
Extracts clean text segments with page numbers and section headings.
"""

import io
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple


class DocumentParsingError(Exception):
    """Raised when document extraction fails or file is malformed."""
    pass


def normalize_text(text: str) -> str:
    """Cleans control characters, normalizes Unicode (NFC), and standardizes whitespace."""
    if not text:
        return ""
    # Normalize unicode to standard composite form
    text = unicodedata.normalize("NFC", text)
    # Remove null bytes and non-printable control characters (except newline, tab, carriage return)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Standardize line endings to \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple consecutive blank lines to at most two
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_pdf(stream_or_path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Extracts text by page from PDF using pypdf."""
    try:
        import pypdf
    except ImportError:
        raise DocumentParsingError("pypdf is required to parse PDF documents.")

    segments: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}

    try:
        if isinstance(stream_or_path, (bytes, bytearray)):
            stream = io.BytesIO(stream_or_path)
        else:
            stream = stream_or_path

        reader = pypdf.PdfReader(stream)
        metadata["page_count"] = len(reader.pages)
        if reader.metadata:
            metadata["title"] = reader.metadata.title or ""
            metadata["author"] = reader.metadata.author or ""

        for page_idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            clean_text = normalize_text(page_text)
            if clean_text:
                segments.append({
                    "text": clean_text,
                    "page_number": page_idx + 1,
                    "heading": None,
                })
    except Exception as e:
        raise DocumentParsingError(f"Failed to parse PDF file: {str(e)}") from e

    return segments, metadata


def parse_docx(stream_or_path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Extracts text and headings from Word (.docx) using python-docx."""
    try:
        import docx
    except ImportError:
        raise DocumentParsingError("python-docx is required to parse DOCX documents.")

    segments: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}

    try:
        if isinstance(stream_or_path, (bytes, bytearray)):
            stream = io.BytesIO(stream_or_path)
        else:
            stream = stream_or_path

        doc = docx.Document(stream)
        current_heading: Optional[str] = None
        current_paragraph_block: List[str] = []

        for p in doc.paragraphs:
            text = normalize_text(p.text)
            if not text:
                continue

            style_name = (p.style.name if p.style else "").lower()
            if "heading" in style_name or "title" in style_name:
                # Flush previous paragraph block if any
                if current_paragraph_block:
                    segments.append({
                        "text": "\n".join(current_paragraph_block),
                        "page_number": None,
                        "heading": current_heading,
                    })
                    current_paragraph_block = []
                current_heading = text
            else:
                current_paragraph_block.append(text)

        if current_paragraph_block:
            segments.append({
                "text": "\n".join(current_paragraph_block),
                "page_number": None,
                "heading": current_heading,
            })

        metadata["paragraph_count"] = len(doc.paragraphs)
        metadata["heading_count"] = sum(1 for s in segments if s.get("heading"))
    except Exception as e:
        raise DocumentParsingError(f"Failed to parse DOCX file: {str(e)}") from e

    return segments, metadata


def parse_plain_text(content_bytes: bytes, is_md: bool = False) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Extracts text from plain text or Markdown with heading detection."""
    try:
        raw_text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            raw_text = content_bytes.decode("latin-1")
        except Exception as e:
            raise DocumentParsingError(f"Encoding error: unable to decode text: {str(e)}")

    clean_text = normalize_text(raw_text)
    segments: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {"line_count": len(clean_text.splitlines())}

    if is_md:
        # Detect Markdown headings (# Heading 1, ## Heading 2)
        current_heading: Optional[str] = None
        current_block: List[str] = []

        for line in clean_text.splitlines():
            line_str = line.strip()
            if line_str.startswith("#"):
                if current_block:
                    segments.append({
                        "text": "\n".join(current_block),
                        "page_number": None,
                        "heading": current_heading,
                    })
                    current_block = []
                current_heading = line_str.lstrip("#").strip()
            else:
                if line_str:
                    current_block.append(line_str)

        if current_block:
            segments.append({
                "text": "\n".join(current_block),
                "page_number": None,
                "heading": current_heading,
            })
    else:
        if clean_text:
            segments.append({
                "text": clean_text,
                "page_number": 1,
                "heading": None,
            })

    return segments, metadata


def parse_document_file(file_obj, file_type: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Unified entrypoint for document parsing.
    Returns (segments, metadata).
    """
    file_type = file_type.upper()
    # Read bytes from file_obj
    if hasattr(file_obj, "read"):
        content_bytes = file_obj.read()
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)
    elif isinstance(file_obj, (bytes, bytearray)):
        content_bytes = bytes(file_obj)
    elif isinstance(file_obj, str):
        with open(file_obj, "rb") as f:
            content_bytes = f.read()
    else:
        raise DocumentParsingError("Unsupported file object type.")

    if not content_bytes:
        raise DocumentParsingError("Uploaded file is empty (0 bytes).")

    if file_type == "PDF":
        return parse_pdf(content_bytes)
    elif file_type == "DOCX":
        return parse_docx(content_bytes)
    elif file_type in ("TXT", "MD"):
        return parse_plain_text(content_bytes, is_md=(file_type == "MD"))
    else:
        raise DocumentParsingError(f"Unsupported file type: '{file_type}'. Supported: PDF, DOCX, TXT, MD.")
