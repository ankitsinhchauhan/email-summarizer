# Email Summarizer

A lightweight web application that summarizes emails, articles, reports, and documents into concise and meaningful text.

## Live Demo

- **Frontend:** [Email Summarizer](https://email-summarizer-ui-ten.vercel.app/)
- **Backend API:** [Render API](https://email-summarizer-api-3x50.onrender.com/)
- **API Documentation:** [Swagger UI](https://email-summarizer-api-3x50.onrender.com/docs)
- **GitHub:** [Repository](https://github.com/ankitsinhchauhan/email-summarizer)

## Features

- Summarize text directly through the web interface.
- Upload and summarize TXT files.
- Upload and summarize text-based PDF files.
- Configurable minimum and maximum summary length.
- Extract important information, decisions, and action items.
- Multi-page PDF text extraction.
- Dark and light themes.
- Responsive user interface.
- File validation and 10 MB upload limit.

## Tech Stack

**Frontend**
- HTML5
- CSS3
- JavaScript

**Backend**
- Python 3.12
- FastAPI
- Uvicorn
- Pydantic
- pypdf

**Testing & Deployment**
- pytest
- Git and GitHub
- Render (Backend)
- Vercel (Frontend)

## Project Structure

```text
email-summarizer/
├── src/
│   ├── api.py
│   ├── pdf_handler.py
│   ├── preprocess.py
│   ├── summarizer.py
│   └── timing.py
├── tests/
├── ui/
│   ├── index.html
│   ├── script.js
│   └── style.css
├── requirements.txt
├── pytest.ini
├── .env.example
└── README.md
```

## Installation

**1. Clone the repository**

```bash
git clone https://github.com/ankitsinhchauhan/email-summarizer.git
cd email-summarizer
```

**2. Create a virtual environment**

```bash
py -3.12 -m venv venv
```

**3. Activate the environment**

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Git Bash:

```bash
source venv/Scripts/activate
```

**4. Install dependencies**

```bash
pip install -r requirements.txt
```

## Run Locally

**1. Start the backend**

```bash
uvicorn src.api:app --reload --host 127.0.0.1 --port 8000
```

Backend: http://127.0.0.1:8000/

API Documentation: http://127.0.0.1:8000/docs

**2. Start the frontend**

Open another terminal:

```bash
python -m http.server 5500 --directory ui
```

Frontend: http://127.0.0.1:5500/

## Run Tests

```bash
pytest -v
```

## Limitations

- Only text-based PDF files are supported.
- Scanned PDFs requiring OCR are not supported.
- Password-protected or encrypted PDFs are not supported.
- Render Free services may experience cold-start delays after inactivity.

## License

No license has been specified yet.

---

**Email Summarizer**