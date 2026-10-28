# Smart Email Summarizer

Smart Email Summarizer is a responsive web application that summarizes long emails, articles, and text documents into concise summaries.

The project features a FastAPI backend and a vanilla HTML5, CSS3, and JavaScript frontend with dark and light theme support.

---

## Features

- **Text Summarization:** Direct text paste with live character count (minimum 200 characters recommended).
- **TXT File Upload:** Dedicated tab for `.txt` plain-text document uploads with file size display and removal control.
- **PDF Document Upload:** Dedicated tab for text-based `.pdf` uploads with memory-safe extraction using `pypdf`.
- **Summary Length Controls:** Configurable Min Length (10–150) and Max Length (50–300) with synchronized client-side and server-side validation.
- **Dark and Light Themes:** Theme toggle with persistent preference stored in `localStorage`.
- **Responsive UI:** Glassmorphism-inspired cyan-to-purple gradient styling optimized for desktop and mobile screens.
- **Fast & Lightweight:** Employs a low-latency heuristic text summarization engine designed to run seamlessly within free-tier serverless and container memory budgets (e.g. Render 512 MB RAM).

---

## Technologies Used

### Frontend
- HTML5 (Semantic tabs and accessible form controls)
- Vanilla CSS3 (Custom properties, gradient themes, glassmorphism, responsive grid/flexbox)
- Vanilla JavaScript (Dynamic environment-aware API resolution, asynchronous fetch, client validation)

### Backend
- Python 3.12
- FastAPI (REST API with CORS middleware)
- Uvicorn (ASGI server)
- Pydantic v2 (Request schema validation)
- pypdf (In-memory readable PDF text extraction)
- pytest (Unit and API integration testing suite)

---

## Project Structure

```text
email-summarizer/
├── src/
│   ├── __init__.py
│   ├── api.py           # FastAPI routes, CORS, and endpoint validation
│   ├── pdf_handler.py   # PDF text extraction, encryption detection, and chunking
│   ├── preprocess.py    # Text sanitization and URL removal
│   └── summarizer.py    # Core summarization logic
├── tests/
│   ├── test_api.py      # Tests for /summarize, /summarize-file, and validation
│   ├── test_pdf.py      # Tests for valid, encrypted, multi-page, and malformed PDFs
│   ├── test_preprocess.py # Tests for text cleaning
│   └── test_summarizer.py # Tests for sentence extraction
├── ui/
│   ├── index.html       # 3-tab user interface (Text, TXT, PDF)
│   ├── script.js        # UI logic, file selection/removal, and API calls
│   └── style.css        # Stylesheet with light/dark theme variables
├── requirements.txt     # Python dependency lockfile
├── pytest.ini           # Pytest configuration
├── .gitignore
└── README.md
```

---

## Supported Input & Limitations

| Input Type | Supported Formats | Maximum Size | Processing Notes |
| :--- | :--- | :--- | :--- |
| **Direct Text** | Plain text | N/A | Minimum 200 characters recommended |
| **TXT File** | `.txt` (UTF-8) | 10 MB | Decoded in-memory |
| **PDF Document** | `.pdf` (text-based) | 10 MB | In-memory text extraction via `pypdf` |

> **PDF Limitation Note:** Scanned or image-only PDFs require Optical Character Recognition (OCR), which is not supported in this lightweight release. Password-protected or encrypted PDFs are safely rejected with an informative error message.

---

## Installation & Setup

### 1. Prerequisites
- Python 3.12 (Python 3.12.7 recommended)
- `pip` package manager

### 2. Activate Virtual Environment

**Windows PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
```

**Git Bash / macOS / Linux:**
```bash
source venv/Scripts/activate  # on Windows Git Bash
# or: source venv/bin/activate
```

*(If creating a fresh virtual environment: `py -3.12 -m venv venv`)*

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## Running Locally

### 1. Start the FastAPI Backend
```bash
uvicorn src.api:app --reload --host 127.0.0.1 --port 8000
```
The API documentation is accessible at `http://127.0.0.1:8000/docs`.

### 2. Start the Frontend Server
In a separate terminal:
```bash
python -m http.server 5500 --directory ui
```
Open your browser and navigate to:
```text
http://127.0.0.1:5500
```

> **API Resolution:** The frontend automatically detects local hostnames (`localhost` or `127.0.0.1`) and routes requests to `http://127.0.0.1:8000`. When hosted in production, it routes requests to the deployed Render backend URL.

---

## Running Tests

Run the complete test suite:
```bash
pytest -v
```

All unit and integration tests run in under 2 seconds without requiring external network access or heavy model downloads.

---

## Live Deployment

- **Frontend (Vercel):** [https://smart-email-summarizer-pi.vercel.app/](https://smart-email-summarizer-pi.vercel.app/)
  - Hosts the static `ui/` bundle with instant CDN distribution.
- **Backend (Render):** [https://smart-email-summarizer-1.onrender.com](https://smart-email-summarizer-1.onrender.com)
  - Runs the FastAPI application with automatic CORS headers for cross-origin requests.
