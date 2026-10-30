from io import BytesIO
from unittest.mock import patch

from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter

from src.api import app, extract_pdf_text


client = TestClient(app)


def make_text_pdf(text: str) -> bytes:
    content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]

    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode())
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010} 00000 n \n".encode())
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode()
    )
    return bytes(pdf)


def make_empty_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def make_multipage_pdf(texts: list) -> bytes:
    writer = PdfWriter()
    for text in texts:
        reader = PdfReader(BytesIO(make_text_pdf(text)))
        writer.add_page(reader.pages[0])
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def make_encrypted_pdf(text: str = "Confidential document text.") -> bytes:
    writer = PdfWriter()
    reader = PdfReader(BytesIO(make_text_pdf(text)))
    writer.add_page(reader.pages[0])
    writer.encrypt("secret_password")
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_valid_pdf_extraction():
    text = extract_pdf_text(make_text_pdf("Readable PDF text for extraction."))
    assert "Readable PDF text" in text


def test_empty_pdf():
    response = client.post(
        "/summarize-pdf",
        files={"file": ("empty.pdf", make_empty_pdf(), "application/pdf")},
    )
    assert response.status_code == 422
    assert "No readable text" in response.json()["detail"]


def test_invalid_pdf():
    response = client.post(
        "/summarize-pdf",
        files={"file": ("broken.pdf", b"%PDF-not-valid", "application/pdf")},
    )
    assert response.status_code == 400
    assert "could not be read" in response.json()["detail"]


def test_pdf_endpoint():
    response = client.post(
        "/summarize-pdf",
        files={
            "file": (
                "message.pdf",
                make_text_pdf(
                    "This is readable PDF content with enough words to pass the "
                    "existing summarizer threshold for this endpoint test."
                ),
                "application/pdf",
            )
        },
    )
    assert response.status_code == 200
    assert response.json()["filename"] == "message.pdf"
    assert "readable PDF content" in response.json()["summary"]


def test_unsupported_file_type():
    response = client.post(
        "/summarize-pdf",
        files={"file": ("message.txt", b"text", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Only .pdf files are supported."


def test_large_file_rejection():
    response = client.post(
        "/summarize-pdf",
        files={
            "file": (
                "large.pdf",
                b"%PDF-" + b"x" * (10 * 1024 * 1024),
                "application/pdf",
            )
        },
    )
    assert response.status_code == 413
    assert "Maximum allowed size is 10 MB" in response.json()["detail"]


def test_encrypted_pdf_rejection():
    encrypted_bytes = make_encrypted_pdf("Encrypted text.")
    response = client.post(
        "/summarize-pdf",
        files={"file": ("encrypted.pdf", encrypted_bytes, "application/pdf")},
    )
    assert response.status_code == 422
    assert "encrypted" in response.json()["detail"].lower()


def test_multipage_pdf_extraction():
    multipage_bytes = make_multipage_pdf([
        "Page one content about enterprise cloud systems.",
        "Page two content regarding automated intelligence models."
    ])
    text = extract_pdf_text(multipage_bytes)
    assert "Page one content" in text
    assert "Page two content" in text


def test_zero_byte_pdf():
    response = client.post(
        "/summarize-pdf",
        files={"file": ("zero.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower() or "not a valid" in response.json()["detail"].lower()


def test_pdf_with_invalid_lengths():
    response = client.post(
        "/summarize-pdf",
        files={
            "file": (
                "sample.pdf",
                make_text_pdf("Valid text inside PDF document."),
                "application/pdf",
            )
        },
        data={"min_length": 100, "max_length": 50},
    )
    assert response.status_code == 422
    assert "smaller than max length" in response.json()["detail"]


def test_pdf_summarize_mocked():
    sample_pdf = make_text_pdf(
        "Artificial intelligence is progressing at a rapid rate worldwide. "
        "Engineers are deploying automated solutions to simplify workflows. "
        "Email summarization helps professionals digest dense inboxes efficiently."
    )
    with patch("src.api.summarize_text", return_value="Mocked AI summary of document.") as mock_sum:
        response = client.post(
            "/summarize-pdf",
            files={"file": ("report.pdf", sample_pdf, "application/pdf")},
        )
        assert response.status_code == 200
        assert response.json()["summary"] == "Mocked AI summary of document."
        mock_sum.assert_called()


def make_symbol_pdf(text: str) -> bytes:
    content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Symbol /Encoding /SymbolSetEncoding >>",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode())
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010} 00000 n \n".encode())
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode()
    )
    return bytes(pdf)


def test_symbol_set_encoding_extraction():
    # Character 0xb7 in Adobe Symbol encoding corresponds to Unicode bullet (•)
    raw_pdf = make_symbol_pdf("Item \xb7 Summary details")
    extracted = extract_pdf_text(raw_pdf)
    assert "\u2022" in extracted or "Item" in extracted


def test_symbol_set_encoding_endpoint():
    symbol_pdf = make_symbol_pdf(
        "Important project release status report with bullet highlights. "
        "Engineers stabilized services and resolved edge-case warnings. "
        "Automated unit testing verifies reliability and end-to-end performance."
    )
    response = client.post(
        "/summarize-pdf",
        files={"file": ("report_symbols.pdf", symbol_pdf, "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["filename"] == "report_symbols.pdf"
    assert len(response.json()["summary"]) > 0


def test_multipage_bounded_chunking():
    # Build 12 pages with substantial content
    pages_content = [
        f"Page {i} details key system developments. Infrastructure was migrated cleanly. Monitoring alerted on zero regressions."
        for i in range(1, 13)
    ]
    multi_pdf = make_multipage_pdf(pages_content)
    response = client.post(
        "/summarize-pdf",
        files={"file": ("multipage_bounded.pdf", multi_pdf, "application/pdf")},
    )
    assert response.status_code == 200
    summary = response.json()["summary"]
    assert "Page 1 details" in summary
    assert summary.endswith(".")


def test_multipage_captures_page2_decision():
    page_1 = (
        "Executive Strategy Memorandum Page 1. "
        "Enterprise computing paradigms have shifted from physical hardware to cloud hosting. "
        "Our organization maintains legacy datacenters across North America and Europe."
    )
    page_2 = (
        "Executive Strategy Memorandum Page 2. "
        "The executive steering committee formally voted to shut down all on-premise datacenters by June 30, 2027. "
        "Chief Financial Officer Walter White authorized a capital budget of $4.2 million for AWS migration services."
    )
    pdf_bytes = make_multipage_pdf([page_1, page_2])
    response = client.post(
        "/summarize-pdf",
        files={"file": ("strategy_memo.pdf", pdf_bytes, "application/pdf")},
        data={"max_length": 150, "min_length": 30},
    )
    assert response.status_code == 200
    summary = response.json()["summary"]
    # Must capture the critical vote and budget from Page 2
    assert "voted to shut down" in summary
    assert "$4.2 million" in summary
    assert "Walter White" in summary