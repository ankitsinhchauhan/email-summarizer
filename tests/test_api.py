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


def test_summarize_text_length_out_of_bounds():
    # min_length below 10
    response = client.post(
        "/summarize",
        json={"text": "Valid text string for summarization.", "max_length": 150, "min_length": 5},
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


def test_summarize_file_mocked():
    with patch("src.api.summarize_text", return_value="Mocked file summary.") as mock_sum:
        response = client.post(
            "/summarize-file",
            files={"file": ("test.txt", b"Sample text content.", "text/plain")},
        )
        assert response.status_code == 200
        assert response.json()["summary"] == "Mocked file summary."
        mock_sum.assert_called_once()
