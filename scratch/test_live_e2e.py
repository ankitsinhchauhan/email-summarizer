import os
import sys
import time
import subprocess
import urllib.request
import urllib.error
import json
from io import BytesIO
from pypdf import PdfWriter, PdfReader

def make_sample_pdf(text: str) -> bytes:
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
    pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode())
    return bytes(pdf)


def run_e2e():
    python_exe = sys.executable
    print(f"Using Python: {python_exe}")

    # 1. Start Backend Server
    backend_cmd = [python_exe, "-m", "uvicorn", "src.api:app", "--host", "127.0.0.1", "--port", "8000"]
    print("Launching backend server...")
    backend_proc = subprocess.Popen(backend_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # 2. Start Frontend Server
    frontend_cmd = [python_exe, "-m", "http.server", "5500", "--directory", "ui"]
    print("Launching frontend server...")
    frontend_proc = subprocess.Popen(frontend_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    results = []

    try:
        # Wait for servers to be up
        backend_ready = False
        frontend_ready = False
        for _ in range(30):
            time.sleep(0.5)
            if not backend_ready:
                try:
                    with urllib.request.urlopen("http://127.0.0.1:8000/") as resp:
                        if resp.status == 200:
                            backend_ready = True
                except Exception:
                    pass
            if not frontend_ready:
                try:
                    with urllib.request.urlopen("http://127.0.0.1:5500/") as resp:
                        if resp.status == 200:
                            frontend_ready = True
                except Exception:
                    pass
            if backend_ready and frontend_ready:
                break

        print(f"Servers ready: Backend={backend_ready}, Frontend={frontend_ready}")
        assert backend_ready, "Backend failed to start on 127.0.0.1:8000"
        assert frontend_ready, "Frontend failed to start on 127.0.0.1:5500"

        # Check 1: Frontend Assets
        with urllib.request.urlopen("http://127.0.0.1:5500/") as resp:
            html = resp.read().decode("utf-8")
            assert "Smart Email Summarizer" in html
            assert "role=\"tablist\"" in html
            assert "role=\"tabpanel\"" in html
            assert "aria-label=\"Email or Article Text\"" in html
            results.append(("Frontend HTML Accessibility & Structure", "PASS"))

        with urllib.request.urlopen("http://127.0.0.1:5500/style.css") as resp:
            css = resp.read().decode("utf-8")
            assert ":focus-visible" in css
            results.append(("Frontend CSS & Visible Focus Styles", "PASS"))

        with urllib.request.urlopen("http://127.0.0.1:5500/script.js") as resp:
            js = resp.read().decode("utf-8")
            assert "API_BASE_URL" in js
            assert "summaryResult.innerText" in js
            results.append(("Frontend JS & XSS Prevention (innerText)", "PASS"))

        # Check 2: CORS Preflight
        req = urllib.request.Request(
            "http://127.0.0.1:8000/summarize",
            method="OPTIONS",
            headers={
                "Origin": "http://127.0.0.1:5500",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        with urllib.request.urlopen(req) as resp:
            allow_origin = resp.headers.get("Access-Control-Allow-Origin")
            allow_creds = resp.headers.get("Access-Control-Allow-Credentials")
            assert allow_origin == "http://127.0.0.1:5500"
            assert allow_creds != "true"
            results.append(("Live CORS Preflight & Credentials Safeguard", "PASS"))

        # Check 2b: CORS Disallow Unknown Origin
        req_bad = urllib.request.Request(
            "http://127.0.0.1:8000/summarize",
            method="OPTIONS",
            headers={
                "Origin": "https://unauthorized-hacker.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        try:
            with urllib.request.urlopen(req_bad) as resp_bad:
                assert resp_bad.headers.get("Access-Control-Allow-Origin") is None
        except urllib.error.HTTPError as err:
            assert err.code == 400
            assert err.headers.get("Access-Control-Allow-Origin") is None
        results.append(("Live CORS Unknown Origin Rejection", "PASS"))

        # Check 3: Text Summarization POST
        import httpx
        sample_email = (
            "Hi team,\n\n"
            "Following up on our sprint review, we have officially approved the release candidate. "
            "The engineering team must deploy the production database migration by Thursday at 2:00 PM. "
            "Total budget approved for infrastructure is $25,000.\n\n"
            "Best regards,\nAlex Vance"
        )
        with httpx.Client(base_url="http://127.0.0.1:8000") as client:
            # 3a. Valid Text Summarization
            resp = client.post(
                "/summarize",
                json={"text": sample_email, "min_length": 15, "max_length": 60},
                headers={"Origin": "http://127.0.0.1:5500"},
            )
            assert resp.status_code == 200, f"Expected 200 got {resp.status_code}"
            data = resp.json()
            assert "summary" in data and len(data["summary"]) > 0
            assert "Alex Vance" not in data["summary"]
            results.append(("Live Text Summarization End-to-End", "PASS"))

            # 3b. Empty Text Validation
            resp_empty = client.post("/summarize", json={"text": "   ", "min_length": 20, "max_length": 60})
            assert resp_empty.status_code == 422
            results.append(("Live Empty Input Validation (422)", "PASS"))

            # 3c. Invalid Length Range Validation
            resp_invalid_len = client.post("/summarize", json={"text": sample_email, "min_length": 100, "max_length": 80})
            assert resp_invalid_len.status_code == 422
            results.append(("Live Min/Max Length Validation (422)", "PASS"))

            # 3d. Live Multipart TXT Upload
            txt_content = b"The strategic planning session reached consensus on Q4 goals. All teams must align deliverables."
            resp_txt = client.post(
                "/summarize-file",
                files={"file": ("notes.txt", txt_content, "text/plain")},
                data={"max_length": "100", "min_length": "20"},
                headers={"Origin": "http://127.0.0.1:5500"},
            )
            assert resp_txt.status_code == 200
            assert resp_txt.json()["filename"] == "notes.txt"
            results.append(("Live TXT Multipart Upload & Summarization", "PASS"))

            # 3e. Live Unsupported Extension Rejection
            resp_bad_ext = client.post(
                "/summarize-file",
                files={"file": ("malicious.exe", b"fake binary", "application/octet-stream")},
            )
            assert resp_bad_ext.status_code == 400
            results.append(("Live TXT File Extension Validation (400)", "PASS"))

            # 3f. Live Multipart PDF Upload
            pdf_bytes = make_sample_pdf(
                "The board approved the quarterly expansion initiative. "
                "Target execution starts November 15th. "
                "All department heads agreed on the proposed timeline and budget allocation."
            )
            resp_pdf = client.post(
                "/summarize-pdf",
                files={"file": ("quarterly_report.pdf", pdf_bytes, "application/pdf")},
                data={"max_length": "100", "min_length": "20"},
                headers={"Origin": "http://127.0.0.1:5500"},
            )
            assert resp_pdf.status_code == 200
            assert resp_pdf.json()["filename"] == "quarterly_report.pdf"
            assert "quarterly expansion" in resp_pdf.json()["summary"].lower()
            results.append(("Live PDF Multipart Upload & Summarization", "PASS"))

            # 3g. Live Malformed PDF Rejection
            resp_bad_pdf = client.post(
                "/summarize-pdf",
                files={"file": ("corrupt.pdf", b"%PDF-invalid-bytes", "application/pdf")},
            )
            assert resp_bad_pdf.status_code == 400
            results.append(("Live Malformed PDF Validation (400)", "PASS"))

        # Check 4: Headless Browser Rendering via Edge/Chrome
        import tempfile
        import shutil
        edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        if not os.path.exists(edge_path):
            edge_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

        if os.path.exists(edge_path):
            temp_profile = tempfile.mkdtemp()
            try:
                browser_cmd = [
                    edge_path,
                    "--headless=new",
                    "--disable-gpu",
                    "--no-sandbox",
                    f"--user-data-dir={temp_profile}",
                    "--dump-dom",
                    "http://127.0.0.1:5500/",
                ]
                print(f"Executing headless browser via: {edge_path}")
                browser_proc = subprocess.run(browser_cmd, capture_output=True, text=True, timeout=15)
                rendered_dom = browser_proc.stdout
                assert "<html" in rendered_dom.lower()
                assert "email summarizer" in rendered_dom.lower()
                assert "generatesummary" in rendered_dom.lower().replace(" ", "")
                assert "email or article text" in rendered_dom.lower()
                results.append((f"Headless Browser Real Engine DOM Render ({os.path.basename(edge_path)})", "PASS"))
            finally:
                shutil.rmtree(temp_profile, ignore_errors=True)
        else:
            results.append(("Headless Browser DOM Verification", "SKIPPED (Browser not found)"))

    finally:
        print("Cleaning up background servers...")
        try:
            backend_proc.terminate()
            backend_proc.wait(timeout=3)
        except Exception:
            backend_proc.kill()
        try:
            frontend_proc.terminate()
            frontend_proc.wait(timeout=3)
        except Exception:
            frontend_proc.kill()

    print("\n" + "=" * 60)
    print("LIVE E2E TEST RESULTS:")
    print("=" * 60)
    for test_name, status in results:
        print(f"  [{status}] {test_name}")
    print("=" * 60)
    return all(s == "PASS" for _, s in results)

if __name__ == "__main__":
    success = run_e2e()
    sys.exit(0 if success else 1)
