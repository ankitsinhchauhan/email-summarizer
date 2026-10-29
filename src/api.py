<<<<<<< HEAD
import time
import anyio
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
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
=======
from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
from src.summarizer import summarize_text
from fastapi.middleware.cors import CORSMiddleware
>>>>>>> origin/main

app = FastAPI(title="Smart Email Summarizer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
<<<<<<< HEAD


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

=======
class SummaryRequest(BaseModel):
    text: str
    max_length: int = 150
    min_length: int = 30
>>>>>>> origin/main

@app.get("/")
def home():
    return {"message": "Smart Email Summarizer Running"}

<<<<<<< HEAD

@app.post("/summarize")
def summarize(request: SummaryRequest):
    t_start = time.perf_counter()
    validate_summary_lengths(request.min_length, request.max_length)

    text = request.text or ""
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Please provide text to summarize.",
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
    file: UploadFile = File(...),
    max_length: int = Form(150),
    min_length: int = Form(30),
):
    t_start = time.perf_counter()
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
    file: UploadFile = File(...),
    max_length: int = Form(150),
    min_length: int = Form(30),
):
    t_start = time.perf_counter()
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
=======
@app.post("/summarize")
def summarize(request: SummaryRequest):
    summary = summarize_text(
        request.text,
        request.max_length,
        request.min_length
    )

    return {
        "original_length": len(request.text),
        "summary": summary
    }

@app.post("/summarize-file")
async def summarize_file(
    file: UploadFile = File(...),
    max_length: int = Form(130),
    min_length: int = Form(30)
):
    content = await file.read()
    text = content.decode("utf-8", errors="ignore")

    summary = summarize_text(text, max_length, min_length)

    return {
        "filename": file.filename,
        "summary": summary
>>>>>>> origin/main
    }

