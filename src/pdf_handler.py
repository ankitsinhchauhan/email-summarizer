import logging
from io import BytesIO
from typing import Callable, List, Optional
from pypdf import PdfReader
from pypdf._codecs import charset_encoding, _symbol_encoding
from pypdf.errors import PdfReadError

# Map /SymbolSetEncoding to Adobe Symbol encoding in pypdf's charset table.
# This prevents repeated "Advanced encoding /SymbolSetEncoding not implemented yet"
# warnings and ensures symbol glyphs (bullets, Greek symbols, math operators) are
# correctly mapped to Unicode rather than discarded or corrupted.
if "/SymbolSetEncoding" not in charset_encoding:
    charset_encoding["/SymbolSetEncoding"] = _symbol_encoding


class _DuplicateLogFilter(logging.Filter):
    """Filter that deduplicates repetitive font/cmap warning logs from pypdf.
    
    Prevents repeated warnings/errors from spamming stderr on every page while
    ensuring each unique warning or encoding limitation is still communicated.
    """
    def __init__(self):
        super().__init__()
        self._seen: set[str] = set()

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if msg in self._seen:
            return False
        self._seen.add(msg)
        return True


_cmap_logger = logging.getLogger("pypdf._cmap")
if not any(isinstance(f, _DuplicateLogFilter) for f in _cmap_logger.filters):
    _cmap_logger.addFilter(_DuplicateLogFilter())


MAX_PDF_SIZE = 10 * 1024 * 1024  # 10 MB
PDF_CHUNK_SIZE = 12000
MAX_PDF_CHUNKS = 10  # Bounded to protect CPU and memory on large multi-page PDFs


class PDFError(Exception):
    """Base exception for PDF processing errors."""
    pass


class PDFSizeLimitExceededError(PDFError):
    """Raised when PDF file size exceeds the allowed limit."""
    pass


class InvalidPDFError(PDFError):
    """Raised when the uploaded file is not a valid PDF or is malformed."""
    pass


class EncryptedPDFError(PDFError):
    """Raised when the PDF file is password-protected or encrypted."""
    pass


class EmptyPDFTextError(PDFError):
    """Raised when no readable text could be extracted (e.g. scanned, image-only)."""
    pass


def validate_pdf_bytes(pdf_bytes: bytes) -> None:
    """Validate that byte stream is not empty and begins with the PDF magic header."""
    if not pdf_bytes:
        raise InvalidPDFError("The uploaded PDF file is empty.")

    if not pdf_bytes.startswith(b"%PDF-"):
        raise InvalidPDFError("The uploaded file is not a valid PDF.")


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract plain text from readable PDF bytes safely using pypdf.
    
    Handles encrypted, malformed, empty, and scanned documents.
    """
    validate_pdf_bytes(pdf_bytes)

    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except Exception as exc:
        raise InvalidPDFError(
            "The PDF could not be read. Please upload a valid PDF file."
        ) from exc

    if getattr(reader, "is_encrypted", False):
        # Attempt to decrypt with empty password (some standard PDFs are marked encrypted without password)
        try:
            decrypt_result = reader.decrypt("")
            # If decrypt returns 0, password is required
            if decrypt_result == 0:
                raise EncryptedPDFError(
                    "Password-protected or encrypted PDFs are not supported. "
                    "Please provide an unencrypted PDF."
                )
        except Exception:
            raise EncryptedPDFError(
                "Password-protected or encrypted PDFs are not supported. "
                "Please provide an unencrypted PDF."
            )

    text_parts: List[str] = []

    try:
        pages = reader.pages
    except Exception as exc:
        raise InvalidPDFError(
            "The PDF structure could not be parsed. Please upload a valid PDF file."
        ) from exc

    for page_idx, page in enumerate(pages):
        try:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text.strip())
        except Exception:
            # Skip unreadable individual page stream without crashing the whole extraction
            continue

    full_text = "\n\n".join(part for part in text_parts if part)

    if not full_text.strip():
        raise EmptyPDFTextError(
            "No readable text was found in this PDF. "
            "The document may be scanned, image-based, or empty, "
            "which requires OCR (not supported in this version)."
        )

    return full_text


def chunk_pdf_text(text: str, chunk_size: int = PDF_CHUNK_SIZE) -> List[str]:
    """Split extracted text into chunks up to chunk_size characters."""
    if not text:
        return []
    return [
        text[i : i + chunk_size]
        for i in range(0, len(text), chunk_size)
    ]


def summarize_pdf_text(
    text: str,
    max_length: int,
    min_length: int,
    summarizer_func: Callable[[str, int, int], str]
) -> str:
    """Chunk and summarize extracted PDF text with bounded chunking and reduction."""
    chunks = chunk_pdf_text(text, PDF_CHUNK_SIZE)
    if not chunks:
        return ""

    # Bound maximum chunks to prevent excessive CPU and memory use on multi-page PDFs
    chunks = chunks[:MAX_PDF_CHUNKS]

    # Summarize the first chunk
    first_summary = summarizer_func(chunks[0], max_length, min_length)
    if len(chunks) == 1:
        return first_summary

    # For multi-chunk documents:
    # If the first chunk's summary already contains at least 3 sentences and is not the "too short" placeholder,
    # the rule-based summarizer reduction (.split(". ")[:3]) will only extract those first 3 sentences.
    # We can return immediately, avoiding redundant chunk summarization and double processing.
    sentences = first_summary.split(". ")
    if len(sentences) >= 3 and first_summary != "Text is too short to summarize.":
        return first_summary

    chunk_summaries: List[str] = []
    if first_summary and first_summary != "Text is too short to summarize.":
        chunk_summaries.append(first_summary)

    for chunk in chunks[1:]:
        c_sum = summarizer_func(chunk, max_length, min_length)
        if c_sum and c_sum != "Text is too short to summarize.":
            chunk_summaries.append(c_sum)
            combined_count = sum(len(s.split(". ")) for s in chunk_summaries)
            if combined_count >= 3:
                break

    if not chunk_summaries:
        return first_summary or "Text is too short to summarize."

    if len(chunk_summaries) == 1:
        return chunk_summaries[0]

    combined_summary = " ".join(chunk_summaries)
    return summarizer_func(combined_summary, max_length, min_length)

