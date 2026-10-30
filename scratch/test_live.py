import httpx
from pypdf import PdfWriter, PdfReader
from io import BytesIO

def make_test_pdf(text: str) -> bytes:
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

def run_tests():
    client = httpx.Client(timeout=10.0)

    print("--- 1. Testing Frontend Static Server (http://127.0.0.1:5500) ---")
    r_front = client.get("http://127.0.0.1:5500/")
    assert r_front.status_code == 200, f"Frontend failed: {r_front.status_code}"
    assert "Email Summarizer" in r_front.text
    print("PASS: Frontend index.html served correctly.")

    print("\n--- 2. Testing Backend Health Endpoint (http://127.0.0.1:8000) ---")
    r_health = client.get("http://127.0.0.1:8000/")
    assert r_health.status_code == 200
    assert r_health.json() == {"message": "Smart Email Summarizer Running"}
    print(f"PASS: Health check response: {r_health.json()}")

    print("\n--- 3. Testing Direct Text Summarization ---")
    long_text = (
        "Good morning everyone. The weather in Austin has been exceptionally pleasant today. "
        "We have detected a critical memory leak in the core caching cluster that requires urgent intervention. "
        "The database operations team has scheduled an emergency maintenance window for tonight, October 30, at 11:00 PM EST. "
        "All engineers must complete the mandatory security patching by 10:30 PM EST. "
        "Unpatched nodes will be automatically quarantined from the production mesh."
    )
    r_sum = client.post(
        "http://127.0.0.1:8000/summarize",
        json={"text": long_text, "max_length": 150, "min_length": 30}
    )
    assert r_sum.status_code == 200, f"Summarize failed: {r_sum.text}"
    data = r_sum.json()
    print("PASS: Summarize response:", data)
    assert "summary" in data and len(data["summary"]) > 0
    # Confirm salutation stripped and action item captured
    assert "must complete the mandatory security patching" in data["summary"]
    assert "Good morning everyone" not in data["summary"]

    print("\n--- 4. Testing Input Validation ---")
    r_empty = client.post(
        "http://127.0.0.1:8000/summarize",
        json={"text": "   ", "max_length": 150, "min_length": 30}
    )
    assert r_empty.status_code == 422
    print("PASS: Empty text rejected with 422:", r_empty.json()["detail"])

    print("\n--- 5. Testing TXT File Upload ---")
    txt_content = (
        "Enterprise cloud services continue to evolve with distributed state machines. "
        "The board of directors formally approved the capital expansion budget of $450,000 for AWS migration. "
        "All department managers must submit final staffing rosters by November 5, 2026."
    ).encode("utf-8")
    r_txt = client.post(
        "http://127.0.0.1:8000/summarize-file",
        files={"file": ("incident_retro.txt", txt_content, "text/plain")},
        data={"max_length": 150, "min_length": 30}
    )
    assert r_txt.status_code == 200
    txt_data = r_txt.json()
    print("PASS: TXT upload response:", txt_data)
    assert txt_data["filename"] == "incident_retro.txt"
    assert "formally approved" in txt_data["summary"]

    print("\n--- 6. Testing PDF Document Upload ---")
    pdf_bytes = make_test_pdf(
        "Quarterly architectural review documents dramatic improvements across services. "
        "The steering committee voted to decommission legacy hardware by June 30, 2027. "
        "CFO Walter White authorized a capital budget of $4.2 million for cloud services."
    )
    r_pdf = client.post(
        "http://127.0.0.1:8000/summarize-pdf",
        files={"file": ("quarterly_review.pdf", pdf_bytes, "application/pdf")},
        data={"max_length": 150, "min_length": 30}
    )
    assert r_pdf.status_code == 200
    pdf_data = r_pdf.json()
    print("PASS: PDF upload response:", pdf_data)
    assert "voted to decommission" in pdf_data["summary"]

    print("\n--- ALL LIVE TESTS PASSED! ---")

if __name__ == "__main__":
    run_tests()

