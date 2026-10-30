from unittest.mock import patch
from fastapi.testclient import TestClient

from src.api import app, validate_summary_lengths

client = TestClient(app)


def test_home_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Smart Email Summarizer Running"}


def test_summarize_text_valid():
    text = (
        "Artificial Intelligence is transforming business across the world. "
        "Natural language processing allows computers to interpret text documents. "
        "Email summarizers save countless hours of reading long threads daily. "
        "Productivity increases as relevant insights are extracted instantly."
    )
    response = client.post(
        "/summarize",
        json={"text": text, "max_length": 150, "min_length": 30},
    )
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert data["original_length"] == len(text)
    assert len(data["summary"]) > 0


def test_summarize_text_empty():
    response = client.post(
        "/summarize",
        json={"text": "   ", "max_length": 150, "min_length": 30},
    )
    assert response.status_code == 422
    assert "provide text" in response.json()["detail"].lower()


def test_summarize_text_invalid_length_order():
    response = client.post(
        "/summarize",
        json={"text": "Valid text string for summarization.", "max_length": 70, "min_length": 80},
    )
    assert response.status_code == 422
    assert "smaller than max length" in response.json()["detail"]


def test_summarize_text_min_length_out_of_bounds():
    # min_length below 10
    response = client.post(
        "/summarize",
        json={"text": "Valid text string for summarization.", "max_length": 150, "min_length": 5},
    )
    assert response.status_code == 422


def test_summarize_text_max_length_out_of_bounds():
    # max_length above 300
    response = client.post(
        "/summarize",
        json={"text": "Valid text string for summarization.", "max_length": 350, "min_length": 50},
    )
    assert response.status_code == 422


def test_summarize_file_valid_txt():
    sample_content = (
        "Here is a comprehensive overview of cloud infrastructure updates. "
        "The team migrated services to modern serverless runtimes. "
        "Performance improved by thirty percent while costs decreased significantly."
    ).encode("utf-8")

    response = client.post(
        "/summarize-file",
        files={"file": ("notes.txt", sample_content, "text/plain")},
        data={"max_length": 150, "min_length": 30},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "notes.txt"
    assert "summary" in data
    assert len(data["summary"]) > 0


def test_summarize_file_unsupported_extension():
    response = client.post(
        "/summarize-file",
        files={"file": ("image.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )
    assert response.status_code == 400
    assert "Only .txt files are supported." in response.json()["detail"]


def test_summarize_file_empty_content():
    response = client.post(
        "/summarize-file",
        files={"file": ("blank.txt", b"   \n\t", "text/plain")},
    )
    assert response.status_code == 422
    assert "No readable text" in response.json()["detail"]


def test_summarize_file_invalid_lengths():
    response = client.post(
        "/summarize-file",
        files={"file": ("notes.txt", b"Some valid content here.", "text/plain")},
        data={"max_length": 50, "min_length": 60},
    )
    assert response.status_code == 422
    assert "smaller than max length" in response.json()["detail"]


def test_summarize_file_too_large():
    response = client.post(
        "/summarize-file",
        files={"file": ("huge.txt", b"A" * (10 * 1024 * 1024 + 1), "text/plain")},
    )
    assert response.status_code == 413
    assert "File is too large" in response.json()["detail"]


def test_summarize_file_missing_file():
    response = client.post("/summarize-file", data={"max_length": 150, "min_length": 30})
    assert response.status_code == 422


def test_summarize_pdf_missing_file():
    response = client.post("/summarize-pdf", data={"max_length": 150, "min_length": 30})
    assert response.status_code == 422


def test_summarize_file_mocked():
    with patch("src.api.summarize_text", return_value="Mocked file summary.") as mock_sum:
        response = client.post(
            "/summarize-file",
            files={"file": ("test.txt", b"Sample text content.", "text/plain")},
        )
        assert response.status_code == 200
        assert response.json()["summary"] == "Mocked file summary."
        mock_sum.assert_called_once()


def test_cors_preflight_and_credentials_header():
    response = client.options(
        "/summarize",
        headers={
            "Origin": "http://localhost:5500",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5500"
    assert response.headers.get("access-control-allow-credentials") is None


def test_cors_preflight_production_origin():
    response = client.options(
        "/summarize",
        headers={
            "Origin": "https://email-summarizer-pi.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://email-summarizer-pi.vercel.app"
    assert response.headers.get("access-control-allow-credentials") is None


def test_cors_disallows_unknown_origins():
    # Preflight from unauthorized origin
    resp_opt = client.options(
        "/summarize",
        headers={
            "Origin": "https://unauthorized-attacker.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp_opt.status_code == 400
    assert resp_opt.headers.get("access-control-allow-origin") is None

    # Normal GET from unauthorized origin
    resp_get = client.get("/", headers={"Origin": "https://unauthorized-attacker.com"})
    assert resp_get.status_code == 200
    assert resp_get.headers.get("access-control-allow-origin") is None

    # Normal POST from unauthorized origin
    resp_post = client.post(
        "/summarize",
        json={"text": "Short valid text string for testing CORS origin rejection.", "min_length": 10, "max_length": 50},
        headers={"Origin": "https://unauthorized-attacker.com"},
    )
    assert resp_post.status_code == 200
    assert resp_post.headers.get("access-control-allow-origin") is None


def test_summarize_missing_fields_payload():
    response = client.post("/summarize", json={})
    assert response.status_code == 422


def test_summarize_invalid_datatype_payload():
    response = client.post("/summarize", json={"text": 12345})
    assert response.status_code == 422


def test_summarize_valid_boundaries():
    text = (
        "Project deployment milestone reached successfully. "
        "The operations team verified database integrity and backups. "
        "Production traffic will shift to the new cluster on Monday at 09:00 AM."
    )
    # Lower boundary: min_length=10, max_length=50
    resp_low = client.post("/summarize", json={"text": text, "min_length": 10, "max_length": 50})
    assert resp_low.status_code == 200

    # Upper boundary: min_length=150, max_length=300
    resp_high = client.post("/summarize", json={"text": text, "min_length": 150, "max_length": 300})
    assert resp_high.status_code == 200


def test_summarize_boundary_failures():
    text = "Valid text for checking boundary limits."
    # min_length < 10
    assert client.post("/summarize", json={"text": text, "min_length": 9, "max_length": 100}).status_code == 422
    # min_length > 150
    assert client.post("/summarize", json={"text": text, "min_length": 151, "max_length": 200}).status_code == 422
    # max_length < 50
    assert client.post("/summarize", json={"text": text, "min_length": 20, "max_length": 49}).status_code == 422
    # max_length > 300
    assert client.post("/summarize", json={"text": text, "min_length": 50, "max_length": 301}).status_code == 422
    # min_length == max_length
    assert client.post("/summarize", json={"text": text, "min_length": 75, "max_length": 75}).status_code == 422


def test_summarize_file_misleading_extensions():
    # Double extension malicious.txt.exe to /summarize-file
    resp1 = client.post(
        "/summarize-file",
        files={"file": ("malicious.txt.exe", b"malicious binary payload", "application/octet-stream")},
    )
    assert resp1.status_code == 400
    assert "Only .txt files are supported" in resp1.json()["detail"]

    # PDF file sent to .txt endpoint
    resp2 = client.post(
        "/summarize-file",
        files={"file": ("report.pdf", b"%PDF-1.4...", "application/pdf")},
    )
    assert resp2.status_code == 400

    # TXT file sent to .pdf endpoint
    resp3 = client.post(
        "/summarize-pdf",
        files={"file": ("notes.txt", b"plain text", "text/plain")},
    )
    assert resp3.status_code == 400
    assert "Only .pdf files are supported" in resp3.json()["detail"]

    # Misleading double extension notes.pdf.txt sent to /summarize-pdf
    resp4 = client.post(
        "/summarize-pdf",
        files={"file": ("notes.pdf.txt", b"plain text", "text/plain")},
    )
    assert resp4.status_code == 400


def test_summarize_unicode_and_punctuation():
    unicode_text = (
        "🚀 Antigravity 2.0 release confirmed! "
        "The engineering leads (Dr. Müller & Ms. Côté) decided to allocate ¥5,000,000 for Tokyo infrastructure. "
        "All security patches must be completed by Friday, Nov 14th at 5:00 PM. "
        "We agree on migrating 100% of the microservices."
    )
    response = client.post(
        "/summarize",
        json={"text": unicode_text, "min_length": 20, "max_length": 100},
    )
    assert response.status_code == 200
    assert "summary" in response.json()
    summary = response.json()["summary"]
    assert len(summary) > 0


def test_summarize_long_text_tail_action_item():
    paragraphs = [
        f"Background information paragraph {i}: Reviewing company progress and quarterly numbers."
        for i in range(1, 15)
    ]
    paragraphs.append("CRITICAL ACTION: Sarah Jenkins must submit the finalized audit report by tomorrow at 4:00 PM.")
    full_text = "\n\n".join(paragraphs)

    response = client.post(
        "/summarize",
        json={"text": full_text, "min_length": 30, "max_length": 150},
    )
    assert response.status_code == 200
    summary = response.json()["summary"]
    assert "Sarah Jenkins" in summary or "audit report" in summary


def test_generic_exception_handler_returns_safe_500():
    safe_client = TestClient(app, raise_server_exceptions=False)
    with patch("src.api.summarize_text", side_effect=RuntimeError("Simulated catastrophic crash")):
        response = safe_client.post(
            "/summarize",
            json={"text": "Test text for simulating unexpected error condition.", "min_length": 10, "max_length": 50},
        )
        assert response.status_code == 500
        assert response.json() == {"detail": "An internal server error occurred."}
        assert "Simulated catastrophic crash" not in response.text


def test_summarize_payload_too_large():
    huge_text = "A" * 500_001
    resp = client.post(
        "/summarize",
        json={"text": huge_text, "min_length": 10, "max_length": 50},
    )
    assert resp.status_code == 413
    assert "Text is too large" in resp.json()["detail"]


def test_rate_limiter_blocks_excessive_requests():
    test_ip = "192.168.100.42"
    with patch("src.api.RATE_LIMIT_PER_MINUTE", 3):
        for _ in range(3):
            r = client.post(
                "/summarize",
                json={"text": "Short valid text sample for testing in-memory rate limiting.", "min_length": 10, "max_length": 50},
                headers={"X-Forwarded-For": test_ip},
            )
            assert r.status_code == 200

        r_blocked = client.post(
            "/summarize",
            json={"text": "Short valid text sample for testing in-memory rate limiting.", "min_length": 10, "max_length": 50},
            headers={"X-Forwarded-For": test_ip},
        )
        assert r_blocked.status_code == 429
        assert "Too many requests" in r_blocked.json()["detail"]
        assert r_blocked.headers.get("retry-after") == "60"


def test_rate_limiter_exempts_health_endpoint():
    test_ip = "192.168.100.99"
    with patch("src.api.RATE_LIMIT_PER_MINUTE", 2):
        for _ in range(5):
            r = client.get("/", headers={"X-Forwarded-For": test_ip})
            assert r.status_code == 200


def test_rate_limiter_spoofed_x_forwarded_for_cannot_bypass():
    # Attacker tries rotating spoofed IP prefixes in X-Forwarded-For,
    # but the connecting proxy IP remains the same (rightmost IP).
    proxy_ip = "203.0.113.195"
    with patch("src.api.RATE_LIMIT_PER_MINUTE", 2):
        # Request 1 with spoofed prefix 1.1.1.1
        r1 = client.post(
            "/summarize",
            json={"text": "Short valid text sample for testing IP spoofing protection.", "min_length": 10, "max_length": 50},
            headers={"X-Forwarded-For": f"1.1.1.1, {proxy_ip}"},
        )
        assert r1.status_code == 200

        # Request 2 with spoofed prefix 2.2.2.2
        r2 = client.post(
            "/summarize",
            json={"text": "Short valid text sample for testing IP spoofing protection.", "min_length": 10, "max_length": 50},
            headers={"X-Forwarded-For": f"2.2.2.2, {proxy_ip}"},
        )
        assert r2.status_code == 200

        # Request 3 with spoofed prefix 3.3.3.3 should still be blocked under true proxy IP
        r3 = client.post(
            "/summarize",
            json={"text": "Short valid text sample for testing IP spoofing protection.", "min_length": 10, "max_length": 50},
            headers={"X-Forwarded-For": f"3.3.3.3, {proxy_ip}"},
        )
        assert r3.status_code == 429


def test_rate_limiter_prioritizes_cf_connecting_ip():
    cf_ip = "198.51.100.77"
    with patch("src.api.RATE_LIMIT_PER_MINUTE", 1):
        r1 = client.post(
            "/summarize",
            json={"text": "Valid text for testing CF-Connecting-IP priority.", "min_length": 10, "max_length": 50},
            headers={"CF-Connecting-IP": cf_ip, "X-Forwarded-For": "10.0.0.1"},
        )
        assert r1.status_code == 200

        # Second request from same CF IP should be throttled
        r2 = client.post(
            "/summarize",
            json={"text": "Valid text for testing CF-Connecting-IP priority.", "min_length": 10, "max_length": 50},
            headers={"CF-Connecting-IP": cf_ip, "X-Forwarded-For": "10.0.0.2"},
        )
        assert r2.status_code == 429
