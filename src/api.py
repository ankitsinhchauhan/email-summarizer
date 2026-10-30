import logging
import os
import time
import anyio
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.preprocess import clean_text
from src.summarizer import summarize_text
from src.timing import log_timing
from src.pdf_handler import (
    MAX_PDF_SIZE,
    PDFError,
    InvalidPDFError,
    EncryptedPDFError,
    EmptyPDFTextError,
    extract_pdf_text,
    summarize_pdf_text,
)

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="Smart Email Summarizer")

# Allowed CORS origins: confirmed production frontend and required local development origins
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://email-summarizer-pi.vercel.app",
]

env_origins = os.getenv("ALLOWED_ORIGINS")
if env_origins:
    ALLOWED_ORIGINS = [
        origin.strip().rstrip("/")
        for origin in env_origins.split(",")
        if origin.strip()
    ]
else:
    ALLOWED_ORIGINS = DEFAULT_ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# In-memory, per-process sliding window rate limiting
# Configured via RATE_LIMIT_PER_MINUTE env var (default: 60 req/min). Set <= 0 to disable.
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
_ip_request_timestamps: dict[str, list[float]] = {}

MAX_RAW_TEXT_CHARS = 500_000  # Enforce maximum text payload to prevent CPU/memory exhaustion


def get_client_ip(request: Request) -> str:
    """Extract client IP securely accounting for trusted reverse proxies.
    
    1. Prioritizes Cloudflare's CF-Connecting-IP header (unforgeable through Cloudflare/Render).
    2. Checks X-Real-IP header set by upstream reverse proxies.
    3. For X-Forwarded-For, uses the rightmost IP (appended by the immediate trusted proxy)
       to avoid trusting client-spoofed prefix IPs.
    4. Falls back to direct socket client host.
    """
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ips = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
        if ips:
            return ips[-1]

    return request.client.host if request.client else "127.0.0.1"


def check_rate_limit(request: Request) -> None:
    """Enforce per-process, in-memory sliding window rate limiting."""
    if RATE_LIMIT_PER_MINUTE <= 0:
        return

    now = time.time()
    window = 60.0
    client_ip = get_client_ip(request)

    timestamps = _ip_request_timestamps.get(client_ip, [])
    valid_timestamps = [ts for ts in timestamps if now - ts < window]

    if len(valid_timestamps) >= RATE_LIMIT_PER_MINUTE:
        _ip_request_timestamps[client_ip] = valid_timestamps
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please wait before submitting another request.",
            headers={"Retry-After": "60"},
        )

    valid_timestamps.append(now)
    _ip_request_timestamps[client_ip] = valid_timestamps

    # Prune inactive IP records if tracking dictionary grows
    if len(_ip_request_timestamps) > 2000:
        stale_ips = [ip for ip, tss in _ip_request_timestamps.items() if not tss or (now - tss[-1] >= window)]
        for ip in stale_ips:
            _ip_request_timestamps.pop(ip, None)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Safe fallback exception handler to prevent leaking internal tracebacks."""
    if isinstance(exc, HTTPException):
        headers = exc.headers or {}
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=headers)
    if isinstance(exc, RequestValidationError):
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": exc.errors()})
    logger.exception("Unhandled server exception on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
    )


def validate_summary_lengths(min_length: int, max_length: int) -> None:
    """Validate min_length and max_length ranges and their relationship."""
    if min_length < 10 or min_length > 150:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Min length must be between 10 and 150.",
        )
    if max_length < 50 or max_length > 300:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Max length must be between 50 and 300.",
        )
    if min_length >= max_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Min length must be smaller than max length.",
        )


class SummaryRequest(BaseModel):
    text: str
    max_length: int = Field(default=150, ge=50, le=300)
    min_length: int = Field(default=30, ge=10, le=150)


@app.get("/")
def home():
    """Health check endpoint."""
    return {"message": "Smart Email Summarizer Running"}


@app.post("/summarize")
def summarize(request: SummaryRequest, req: Request):
    """Summarize raw text provided in the request body."""
    t_start = time.perf_counter()
    check_rate_limit(req)
    validate_summary_lengths(request.min_length, request.max_length)

    text = request.text or ""
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Please provide text to summarize.",
        )

    if len(text) > MAX_RAW_TEXT_CHARS:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Text is too large. Maximum allowed size is {MAX_RAW_TEXT_CHARS:,} characters.",
        )

    t_sum_start = time.perf_counter()
    summary = summarize_text(
        text,
        request.max_length,
        request.min_length,
    )
    t_sum_end = time.perf_counter()

    t_total = time.perf_counter() - t_start
    log_timing(
        "/summarize",
        t_total,
        {"summarize": t_sum_end - t_sum_start},
        chars=len(text),
    )

    return {
        "original_length": len(text),
        "summary": summary,
    }


@app.post("/summarize-file")
async def summarize_file(
    req: Request,
    file: UploadFile = File(...),
    max_length: int = Form(150),
    min_length: int = Form(30),
):
    """Summarize text extracted from an uploaded plain text (.txt) file."""
    t_start = time.perf_counter()
    check_rate_limit(req)
    validate_summary_lengths(min_length, max_length)

    filename = file.filename or ""
    if not filename.lower().endswith(".txt"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .txt files are supported.",
        )

    # Enforce maximum text file size (10 MB)
    t_read_start = time.perf_counter()
    content = await file.read(MAX_PDF_SIZE + 1)
    t_read_end = time.perf_counter()

    if len(content) > MAX_PDF_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File is too large. Maximum allowed size is 10 MB.",
        )

    t_decode_start = time.perf_counter()
    text = content.decode("utf-8", errors="ignore")
    t_decode_end = time.perf_counter()

    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No readable text was found in this file.",
        )

    t_sum_start = time.perf_counter()
    summary = await anyio.to_thread.run_sync(
        summarize_text, text, max_length, min_length
    )
    t_sum_end = time.perf_counter()

    t_total = time.perf_counter() - t_start
    log_timing(
        "/summarize-file",
        t_total,
        {
            "read": t_read_end - t_read_start,
            "decode": t_decode_end - t_decode_start,
            "summarize": t_sum_end - t_sum_start,
        },
        bytes=len(content),
        chars=len(text),
    )

    return {
        "filename": filename,
        "summary": summary,
    }


@app.post("/summarize-pdf")
async def summarize_pdf(
    req: Request,
    file: UploadFile = File(...),
    max_length: int = Form(150),
    min_length: int = Form(30),
):
    """Extract and summarize text from an uploaded PDF document."""
    t_start = time.perf_counter()
    check_rate_limit(req)
    validate_summary_lengths(min_length, max_length)

    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .pdf files are supported.",
        )

    # Read up to MAX_PDF_SIZE + 1 to enforce size limit before parsing
    t_read_start = time.perf_counter()
    pdf_bytes = await file.read(MAX_PDF_SIZE + 1)
    t_read_end = time.perf_counter()

    if len(pdf_bytes) > MAX_PDF_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="PDF file is too large. Maximum allowed size is 10 MB.",
        )

    t_extract_start = time.perf_counter()
    try:
        text = await anyio.to_thread.run_sync(extract_pdf_text, pdf_bytes)
    except InvalidPDFError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except EncryptedPDFError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except EmptyPDFTextError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except PDFError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The PDF could not be read. Please upload a valid PDF file.",
        ) from exc
    t_extract_end = time.perf_counter()

    t_sum_start = time.perf_counter()
    summary = await anyio.to_thread.run_sync(
        summarize_pdf_text, text, max_length, min_length, summarize_text
    )
    t_sum_end = time.perf_counter()

    t_total = time.perf_counter() - t_start
    log_timing(
        "/summarize-pdf",
        t_total,
        {
            "read": t_read_end - t_read_start,
            "extract": t_extract_end - t_extract_start,
            "summarize": t_sum_end - t_sum_start,
        },
        bytes=len(pdf_bytes),
        chars=len(text),
    )

    return {
        "filename": filename,
        "summary": summary,
    }
