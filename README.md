# Smart Email Summarizer

Smart Email Summarizer is a responsive, fast, and memory-safe web application that extracts high-value summaries from emails, articles, reports, and documents.

The project features a **FastAPI** backend and a lightweight vanilla **HTML5, CSS3, and JavaScript** frontend with dark and light theme support.

---

## Features

- **Action-Oriented Sentence Ranking:** Identifies and prioritizes critical business decisions, action items, deadlines, dates, financial amounts, and leadership directives across the entire document.
- **Envelope Sanitization:** Conservatively removes introductory email greetings (e.g., *"Hi Team,"*, *"Dear Alexander,"*) and trailing signatures (e.g., *"Best regards,"*, *"Sincerely,"*) to maximize summary information density.
- **Robust Sentence Boundary Segmentation:** Accurately segments sentences with periods, question marks, and exclamation marks while protecting abbreviations (`Dr.`, `Mr.`, `e.g.`, `i.e.`), dates (`Oct.`, `Dec.`), and decimal numbers (`$1.5M`, `2.3%`).
- **Enforced Word Length Controls:** Configurable Min Length (10–150 words) and Max Length (50–300 words) strictly respected by the backend greedy budget accumulator.
- **Multi-Page PDF Aggregation:** Evaluates candidate sentences across all pages and chunks in multi-page PDFs, ensuring decisions appearing on later pages are captured.
- **Direct Text Summarization:** Live character count with minimum 200 characters recommended.
- **TXT & PDF File Uploads:** Dedicated tabs with file size display, format validation, and removal buttons (up to 10 MB).
- **Dark and Light Themes:** Glassmorphism styling with persistent theme storage in `localStorage`.
- **Low Memory Overhead:** Uses $< 10$ MB RAM during inference, operating safely within container and serverless free-tier constraints (e.g., Render 512 MB RAM).
- **Structured Timing Telemetry:** Phase-by-phase execution metrics without logging document contents.

---

## Technologies Used

### Frontend
- **HTML5:** Semantic tabs, accessible form controls, ARIA attributes.
- **Vanilla CSS3:** Custom properties, responsive flexbox/grid, glassmorphism gradient theme.
- **Vanilla JavaScript:** Environment-aware dynamic API URL routing, asynchronous fetch, client validation.

### Backend
- **Python 3.12:** Verified on Python 3.12.7.
- **FastAPI:** High-performance REST API with CORS middleware and Pydantic validation.
- **Uvicorn:** Production-ready ASGI web server.
- **pypdf:** In-memory readable PDF text extraction with symbol encoding patch and duplicate warning suppression.
- **pytest:** Comprehensive unit and regression test suite (53 tests).

---

## Project Structure

```text
email-summarizer/
├── src/
│   ├── __init__.py
│   ├── api.py           # FastAPI routes, CORS, and endpoint validation
│   ├── pdf_handler.py   # Multi-chunk PDF extraction and aggregation
│   ├── preprocess.py    # Envelope cleaning, salutation/signature stripping, URL removal
│   ├── summarizer.py    # Action-oriented sentence tokenizer and extractive ranker
│   └── timing.py        # Structured stage-by-stage timing metrics
├── tests/
│   ├── data/pdfs/       # Generated PDF test assets (text, multipage, encrypted, scanned)
│   ├── evaluation_dataset.json # 32-sample benchmark with human reference summaries
│   ├── test_api.py      # API tests for /summarize, /summarize-file, /summarize-pdf, and validation
│   ├── test_pdf.py      # PDF extraction, multipage decisions, and encryption tests
│   ├── test_preprocess.py # Tests for text cleaning, greetings, signatures, and URLs
│   └── test_summarizer.py # Tests for tokenization, length controls, decisions, and ranking
├── ui/
│   ├── index.html       # 3-tab user interface (Text, TXT, PDF)
│   ├── script.js        # UI logic, environment detection, and API calls
│   └── style.css        # Stylesheet with light/dark theme variables
├── scratch/
│   ├── evaluate_summarizer.py # Automated 32-sample benchmark runner
│   ├── evaluation_results.json # Measured benchmark results
│   └── test_live.py     # Live integration verification script
├── .env.example         # Example environment variables
├── .gitignore           # Git ignore patterns
├── pytest.ini           # Pytest configuration
├── requirements.txt     # Python dependency lockfile
└── README.md            # Project documentation
```

---

## Supported Input & Limitations

| Input Type | Supported Formats | Maximum Size | Processing Notes |
| :--- | :--- | :--- | :--- |
| **Direct Text** | Plain text | N/A | Minimum 200 characters recommended |
| **TXT File** | `.txt` (UTF-8) | 10 MB | Decoded in-memory |
| **PDF Document** | `.pdf` (text-based) | 10 MB | Multi-page text extraction and chunk aggregation |

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
source venv/Scripts/activate
```

*(To create a fresh virtual environment: `py -3.12 -m virtualenv venv`)*

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

Verify that all dependencies are installed cleanly:
```bash
python -m pip check
```

---

## Running Locally

### 1. Start the FastAPI Backend
From the project root:
```bash
uvicorn src.api:app --reload --host 127.0.0.1 --port 8000
```
- API health check: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Interactive API Documentation (Swagger UI): [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 2. Start the Frontend Server
In a separate terminal:
```bash
python -m http.server 5500 --directory ui
```
Open your browser and navigate to:
```text
http://127.0.0.1:5500/
```

> **Dynamic API Resolution:** The frontend automatically detects local hostnames (`localhost` or `127.0.0.1`) and routes requests to `http://127.0.0.1:8000`. When hosted in production, it routes requests to the deployed Render backend URL.

---

## Running Tests & Evaluation Benchmark

### 1. Run the Unit & Integration Test Suite
```bash
pytest -v
```
All 53 unit and integration tests run in under 2 seconds.

### 2. Run the 32-Sample Accuracy Benchmark
```bash
python scratch/evaluate_summarizer.py
```
This evaluates ROUGE-1, ROUGE-2, ROUGE-L, Action-Item Recall, Decision Recall, Dates/Deadlines Recall, and Multi-page PDF coverage against human reference summaries.

---

## Measured Benchmark Performance

Evaluation across the 32 representative documents in [`tests/evaluation_dataset.json`](tests/evaluation_dataset.json):

| Metric | Lead-3 Baseline | Improved Action-Oriented Ranker | Measured Change |
| :--- | :---: | :---: | :---: |
| **ROUGE-1 F1** | 29.24% | **51.47%** | **+22.23%** |
| **ROUGE-2 F1** | 12.25% | **30.22%** | **+17.97%** |
| **ROUGE-L F1** | 21.12% | **42.94%** | **+21.82%** |
| **Action Items Recall** | 0.0% (0/37) | **83.8% (31/37)** | **+83.8%** |
| **Decisions Recall** | 0.0% (0/32) | **81.2% (26/32)** | **+81.2%** |
| **Deadlines & Dates Recall** | 20.9% (18/86) | **73.3% (63/86)** | **+52.4%** |
| **Amounts & Numbers Recall** | 42.9% (39/91) | **61.5% (56/91)** | **+18.6%** |
| **Names & Entities Recall** | 50.0% (47/94) | **60.6% (57/94)** | **+10.6%** |
| **Salutation Noise Instances** | 10 | **0** | **-10 (Eliminated)** |
| **Length Controls Ignored** | 15 | **0** | **-15 (Eliminated)** |
| **Multi-Page Truncations** | 1 | **0** | **-1 (Eliminated)** |

---

## Live Deployment

- **Frontend (Vercel):** [https://email-summarizer-pi.vercel.app/](https://email-summarizer-pi.vercel.app/)
  - Hosts the static `ui/` bundle with instant CDN distribution.
- **Backend (Render):** [https://smart-email-summarizer-1.onrender.com](https://smart-email-summarizer-1.onrender.com)
  - Runs the FastAPI application with automatic CORS headers for cross-origin requests.
