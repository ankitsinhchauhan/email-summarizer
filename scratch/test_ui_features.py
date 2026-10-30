import os
import sys

def verify_frontend_code_integrity():
    print("Testing frontend code integrity and feature completeness...")

    with open("ui/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    with open("ui/style.css", "r", encoding="utf-8") as f:
        css = f.read()

    with open("ui/script.js", "r", encoding="utf-8") as f:
        js = f.read()

    # 1. Structure & Accessibility Checks
    assert "<!doctype html>" in html.lower()
    assert 'lang="en"' in html
    assert 'data-theme="dark"' in html
    assert 'role="tablist"' in html
    assert 'role="tabpanel"' in html
    assert 'role="dialog"' in html
    assert 'aria-modal="true"' in html
    assert 'aria-live="polite"' in html
    assert 'id="uploadModalOverlay"' in html
    assert 'id="modalDropzone"' in html
    assert 'id="modalBrowseBtn"' in html
    assert 'id="uploadBtnTxt"' in html
    assert 'id="uploadBtnPdf"' in html
    assert 'id="copySummaryBtn"' in html
    assert 'id="uploadProgressBox"' in html
    assert 'id="progressBar"' in html
    assert 'id="toastNotification"' in html
    print("  [PASS] HTML semantic structure, ARIA accessibility, and dialog modals")

    # 2. CSS Design System & Theme Variables
    assert ":root" in css
    assert "body.dark" in css
    assert '[data-theme="dark"]' in css
    assert "--accent: #635bff" in css
    assert "--panel:" in css
    assert ":focus-visible" in css
    assert ".dropzone.drag" in css
    assert ".progress-bar.processing" in css
    assert ".toast" in css
    assert ".toast.show" in css
    assert ".backdrop" in css
    assert ".modal" in css
    assert "@media (max-width: 800px)" in css
    assert "@media (max-width: 520px)" in css
    print("  [PASS] CSS Design tokens, Dark/Light modes, animations, and responsive breakpoints")

    # 3. JS Architecture & Functional Capabilities
    assert "isLocalhost" in js
    assert "http://127.0.0.1:8000" in js
    assert "https://email-summarizer-api-3x50.onrender.com" in js
    assert "MAX_FILE_SIZE = 10 * 1024 * 1024" in js

    # Check Tab switching & localStorage persistence
    assert 'localStorage.getItem("activeMode")' in js
    assert 'localStorage.setItem("activeMode", targetTab)' in js

    # Check Theme persistence
    assert 'localStorage.getItem("theme")' in js
    assert 'localStorage.setItem("theme"' in js

    # Check Drag and Drop
    assert "dragover" in js
    assert "dragleave" in js
    assert "drop" in js

    # Check Modal dialog handling
    assert "openUploadModal" in js
    assert "closeUploadModal" in js
    assert "Escape" in js

    # Check Real XHR progress tracking
    assert "XMLHttpRequest" in js
    assert "xhr.upload.onprogress" in js
    assert "lengthComputable" in js

    # Check Copy to clipboard
    assert "navigator.clipboard.writeText" in js
    assert "Copied!" in js

    # Check Toast notifications
    assert "notifyToast" in js
    assert "toastNotification" in js

    # Check DOM-based XSS Prevention
    assert "summaryResult.innerText" in js
    assert "innerHTML = summary" not in js
    assert "innerHTML=summary" not in js
    print("  [PASS] JavaScript features: XHR progress, tab persistence, modal, toast, and XSS safeguards")

    print("\nAll UI Code Integrity Checks Passed Successfully!")
    return True

if __name__ == "__main__":
    if not verify_frontend_code_integrity():
        sys.exit(1)
    sys.exit(0)
