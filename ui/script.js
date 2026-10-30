// ==========================================================================
// SMART EMAIL SUMMARIZER — PRODUCTION CLIENT CONTROLLER
// Handles API requests, real XHR upload tracking, modal workflows,
// drag-and-drop, theme persistence, and accessible UI interactions.
// ==========================================================================

// --------------------------------------------------------------------------
// 1. Environment-Aware Configuration
// --------------------------------------------------------------------------

const isLocalhost =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1" ||
  window.location.hostname === "";

const API_BASE_URL = isLocalhost
  ? "http://127.0.0.1:8000"
  : "https://email-summarizer-api-3x50.onrender.com";

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

// --------------------------------------------------------------------------
// 2. DOM Elements Selection
// --------------------------------------------------------------------------

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

// Header & Theme
const themeToggle = $("#themeToggle");

// Tabs & Panels
const tabs = $$(".tab");
const textTab = $("#textTab");
const txtTab = $("#txtTab");
const pdfTab = $("#pdfTab");
const panelText = $("#panel-text");
const panelTxt = $("#panel-txt");
const panelPdf = $("#panel-pdf");

// Direct Text Input
const inputText = $("#inputText");
const charCount = $("#charCount");

// Length Budget Controls
const minLengthInput = $("#minLength");
const maxLengthInput = $("#maxLength");
const summarizeBtn = $("#summarizeBtn");
const errorMessage = $("#errorMessage");

// Upload Progress
const uploadProgressBox = $("#uploadProgressBox");
const progressStatus = $("#progressStatus");
const progressPercent = $("#progressPercent");
const progressBar = $("#progressBar");

// Result Card & Stats
const emptyState = $("#emptyState");
const resultCard = $("#resultCard");
const resultStatus = $("#resultStatus");
const summaryResult = $("#summaryResult");
const copySummaryBtn = $("#copySummaryBtn");
const originalStat = $("#original");
const summarizedStat = $("#summarized");
const reductionStat = $("#reduction");

// Modal Dialog Elements
const uploadModalOverlay = $("#uploadModalOverlay");
const modalTitle = $("#modalTitle");
const modalDesc = $("#modalDesc");
const modalCloseBtn = $("#modalCloseBtn");
const modalCancelBtn = $("#modalCancelBtn");
const modalUseBtn = $("#modalUseBtn");
const modalBrowseBtn = $("#modalBrowseBtn");
const modalClearBtn = $("#modalClearBtn");
const modalDropzone = $("#modalDropzone");
const modalChip = $("#modalChip");
const modalExt = $("#modalExt");
const modalName = $("#modalName");
const modalSize = $("#modalSize");
const filePicker = $("#filePicker");

// Toast Container
const toastNotification = $("#toastNotification");

// --------------------------------------------------------------------------
// 3. Application State
// --------------------------------------------------------------------------

let currentTab = localStorage.getItem("activeMode") || "text";
if (!["text", "txt", "pdf"].includes(currentTab)) {
  currentTab = "text";
}

let modalKind = "txt"; // "txt" | "pdf"
let modalCandidate = null;

const attachedFiles = {
  txt: null,
  pdf: null,
};

// --------------------------------------------------------------------------
// 4. Initialization
// --------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  switchTab(currentTab);
  initInputListeners();
  initModalHandlers();
  initPanelDropzones();
});

// Immediately initialize theme and active tab for instant render
initTheme();
switchTab(currentTab);

// --------------------------------------------------------------------------
// 5. Theme Management & Persistence
// --------------------------------------------------------------------------

function initTheme() {
  const savedTheme = localStorage.getItem("theme") || "dark";
  applyTheme(savedTheme);
}

function applyTheme(theme) {
  const isDark = theme === "dark";
  document.body.classList.toggle("dark", isDark);
  document.documentElement.setAttribute("data-theme", isDark ? "dark" : "light");
  if (themeToggle) {
    themeToggle.textContent = isDark ? "☀" : "☾";
  }
  localStorage.setItem("theme", isDark ? "dark" : "light");
}

if (themeToggle) {
  themeToggle.addEventListener("click", () => {
    const isDark = document.body.classList.contains("dark");
    applyTheme(isDark ? "light" : "dark");
  });
}

// --------------------------------------------------------------------------
// 6. Mode Tabs Switching
// --------------------------------------------------------------------------

function switchTab(targetTab) {
  currentTab = targetTab;
  localStorage.setItem("activeMode", targetTab);

  tabs.forEach((tabBtn) => {
    const isActive = tabBtn.dataset.tab === targetTab;
    tabBtn.classList.toggle("active", isActive);
    tabBtn.setAttribute("aria-selected", isActive ? "true" : "false");
  });

  const panels = [
    { name: "text", el: panelText },
    { name: "txt", el: panelTxt },
    { name: "pdf", el: panelPdf },
  ];

  panels.forEach(({ name, el }) => {
    if (el) {
      el.classList.toggle("active", name === targetTab);
    }
  });

  clearError();
}

tabs.forEach((tabBtn) => {
  tabBtn.addEventListener("click", () => {
    switchTab(tabBtn.dataset.tab);
  });
});

// --------------------------------------------------------------------------
// 7. Input Handlers & Validation
// --------------------------------------------------------------------------

function initInputListeners() {
  if (inputText) {
    inputText.addEventListener("input", (e) => {
      const len = e.target.value.length;
      if (charCount) {
        charCount.textContent = `${len.toLocaleString()} characters`;
      }
      clearError();
    });
  }

  if (minLengthInput) {
    minLengthInput.addEventListener("input", clearError);
  }
  if (maxLengthInput) {
    maxLengthInput.addEventListener("input", clearError);
  }
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(2)} MB`;
}

function getLengths() {
  const minVal = parseInt(minLengthInput ? minLengthInput.value : "30", 10);
  const maxVal = parseInt(maxLengthInput ? maxLengthInput.value : "150", 10);
  return { minVal, maxVal };
}

function validateLengths(minVal, maxVal) {
  clearError();

  if (Number.isNaN(minVal) || Number.isNaN(maxVal)) {
    showError("Please enter valid numeric values for min and max words.");
    return false;
  }

  if (minVal < 10 || minVal > 150) {
    showError("Min length must be between 10 and 150 words.");
    return false;
  }

  if (maxVal < 50 || maxVal > 300) {
    showError("Max length must be between 50 and 300 words.");
    return false;
  }

  if (minVal >= maxVal) {
    showError("Min length must be smaller than max length.");
    return false;
  }

  return true;
}

// --------------------------------------------------------------------------
// 8. Reusable Upload Modal & Drag-and-Drop
// --------------------------------------------------------------------------

function openUploadModal(type) {
  modalKind = type;
  modalCandidate = attachedFiles[type];

  if (modalTitle) {
    modalTitle.textContent = type === "pdf" ? "Upload a PDF document" : "Upload a TXT file";
  }
  if (modalDesc) {
    modalDesc.textContent =
      (type === "pdf" ? "Text-based PDFs only" : "Plain text files (.txt)") +
      " &middot; Maximum file size 10 MB";
  }
  if (filePicker) {
    filePicker.accept = type === "pdf" ? ".pdf,application/pdf" : ".txt,text/plain";
    filePicker.value = ""; // Reset so same file can be selected again
  }

  renderModalCandidate();

  if (uploadModalOverlay) {
    uploadModalOverlay.classList.add("open");
    document.body.style.overflow = "hidden";
  }
}

function closeUploadModal() {
  modalCandidate = null;
  if (uploadModalOverlay) {
    uploadModalOverlay.classList.remove("open");
    document.body.style.overflow = "";
  }
}

function acceptFileCandidate(file) {
  if (!file) return;

  const expectedExt = modalKind === "pdf" ? ".pdf" : ".txt";
  if (!file.name.toLowerCase().endsWith(expectedExt)) {
    notifyToast(`Please choose a ${expectedExt} file.`);
    return;
  }

  if (file.size > MAX_FILE_SIZE) {
    notifyToast("File is larger than 10 MB limit.");
    return;
  }

  modalCandidate = file;
  renderModalCandidate();
}

function renderModalCandidate() {
  if (!modalChip || !modalUseBtn) return;

  const hasCandidate = !!modalCandidate;
  modalChip.classList.toggle("show", hasCandidate);
  modalUseBtn.disabled = !hasCandidate;

  if (hasCandidate) {
    if (modalExt) modalExt.textContent = modalKind.toUpperCase();
    if (modalName) modalName.textContent = modalCandidate.name;
    if (modalSize) modalSize.textContent = formatBytes(modalCandidate.size);
  }
}

function attachFileToPanel(kind, file) {
  attachedFiles[kind] = file;
  const chip = $(`#chip-${kind}`);
  const nameEl = $(`#name-${kind}`);
  const sizeEl = $(`#size-${kind}`);

  if (chip && nameEl && sizeEl) {
    nameEl.textContent = file.name;
    sizeEl.textContent = formatBytes(file.size);
    chip.classList.add("show");
  }

  clearError();
}

function removeAttachedFile(kind) {
  attachedFiles[kind] = null;
  const chip = $(`#chip-${kind}`);
  if (chip) {
    chip.classList.remove("show");
  }
  if (filePicker) {
    filePicker.value = "";
  }
  clearError();
  notifyToast("File removed");
}

function initModalHandlers() {
  // Open modal buttons
  $$("[data-open]").forEach((btn) => {
    btn.addEventListener("click", () => openUploadModal(btn.dataset.open));
  });

  // Close modal buttons
  if (modalCloseBtn) modalCloseBtn.addEventListener("click", closeUploadModal);
  if (modalCancelBtn) modalCancelBtn.addEventListener("click", closeUploadModal);

  // Overlay click dismiss
  if (uploadModalOverlay) {
    uploadModalOverlay.addEventListener("click", (e) => {
      if (e.target === uploadModalOverlay) {
        closeUploadModal();
      }
    });
  }

  // Escape key dismiss
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && uploadModalOverlay && uploadModalOverlay.classList.contains("open")) {
      closeUploadModal();
    }
  });

  // Browse files
  if (modalBrowseBtn && filePicker) {
    modalBrowseBtn.addEventListener("click", () => filePicker.click());
  }

  if (filePicker) {
    filePicker.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        acceptFileCandidate(e.target.files[0]);
      }
    });
  }

  // Modal clear candidate
  if (modalClearBtn) {
    modalClearBtn.addEventListener("click", () => {
      modalCandidate = null;
      if (filePicker) filePicker.value = "";
      renderModalCandidate();
    });
  }

  // Modal confirm use file
  if (modalUseBtn) {
    modalUseBtn.addEventListener("click", () => {
      if (!modalCandidate) return;
      attachFileToPanel(modalKind, modalCandidate);
      closeUploadModal();
      notifyToast("File added successfully");
    });
  }

  // Modal dropzone drag & drop
  if (modalDropzone) {
    ["dragenter", "dragover"].forEach((evt) => {
      modalDropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        modalDropzone.classList.add("drag");
      });
    });

    ["dragleave", "drop"].forEach((evt) => {
      modalDropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        modalDropzone.classList.remove("drag");
      });
    });

    modalDropzone.addEventListener("drop", (e) => {
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        acceptFileCandidate(e.dataTransfer.files[0]);
      }
    });
  }

  // Remove buttons on panel chips
  $$("[data-remove]").forEach((btn) => {
    btn.addEventListener("click", () => {
      removeAttachedFile(btn.dataset.remove);
    });
  });
}

// Panel dropzones (direct drag & drop onto .upload buttons)
function initPanelDropzones() {
  $$(".upload").forEach((uploadBox) => {
    const kind = uploadBox.dataset.open;

    ["dragenter", "dragover"].forEach((evt) => {
      uploadBox.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadBox.classList.add("drag");
      });
    });

    ["dragleave", "drop"].forEach((evt) => {
      uploadBox.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadBox.classList.remove("drag");
      });
    });

    uploadBox.addEventListener("drop", (e) => {
      const files = e.dataTransfer ? e.dataTransfer.files : null;
      if (files && files.length > 0) {
        const file = files[0];
        const expectedExt = kind === "pdf" ? ".pdf" : ".txt";

        if (!file.name.toLowerCase().endsWith(expectedExt)) {
          notifyToast(`Please drop a valid ${expectedExt} file.`);
          return;
        }

        if (file.size > MAX_FILE_SIZE) {
          notifyToast("File exceeds 10 MB limit.");
          return;
        }

        attachFileToPanel(kind, file);
        notifyToast("File added successfully");
      }
    });
  });
}

// --------------------------------------------------------------------------
// 9. Summarization Dispatcher
// --------------------------------------------------------------------------

if (summarizeBtn) {
  summarizeBtn.addEventListener("click", async () => {
    if (currentTab === "text") {
      await summarizeTextInput();
    } else if (currentTab === "txt") {
      await summarizeTxtInput();
    } else if (currentTab === "pdf") {
      await summarizePdfInput();
    }
  });
}

// Direct Text Summarization
async function summarizeTextInput() {
  const text = inputText ? inputText.value.trim() : "";
  const { minVal, maxVal } = getLengths();

  if (!validateLengths(minVal, maxVal)) return;

  if (text.length < 200) {
    showError("Please enter at least 200 characters.");
    notifyToast("Please enter at least 200 characters.");
    return;
  }

  startLoading();

  try {
    const response = await fetch(`${API_BASE_URL}/summarize`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text: text,
        max_length: maxVal,
        min_length: minVal,
      }),
    });

    if (!response.ok) {
      throw new Error(await extractErrorDetail(response));
    }

    const data = await response.json();
    renderSummaryResult(data.summary, text.length, "Direct Text");
    notifyToast("Summary generated successfully");
  } catch (err) {
    showError(err.message);
    notifyToast(err.message);
  } finally {
    stopLoading();
  }
}

// TXT File Summarization
async function summarizeTxtInput() {
  const file = attachedFiles.txt;
  const { minVal, maxVal } = getLengths();

  if (!validateLengths(minVal, maxVal)) return;

  if (!file) {
    showError("Please upload a .txt file first.");
    notifyToast("Please upload a .txt file first.");
    return;
  }

  let originalCharCount = file.size;
  try {
    const fileContent = await file.text();
    originalCharCount = fileContent.length;
  } catch {
    originalCharCount = file.size;
  }

  uploadFileWithXHR(file, minVal, maxVal, "/summarize-file", originalCharCount);
}

// PDF Document Summarization
async function summarizePdfInput() {
  const file = attachedFiles.pdf;
  const { minVal, maxVal } = getLengths();

  if (!validateLengths(minVal, maxVal)) return;

  if (!file) {
    showError("Please upload a .pdf document first.");
    notifyToast("Please upload a .pdf document first.");
    return;
  }

  uploadFileWithXHR(file, minVal, maxVal, "/summarize-pdf", file.size);
}

// --------------------------------------------------------------------------
// 10. Real Upload Progress Bar with XMLHttpRequest
// --------------------------------------------------------------------------

function uploadFileWithXHR(file, minLength, maxLength, endpoint, originalSize) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("max_length", maxLength);
  formData.append("min_length", minLength);

  startLoading();
  showProgress(0, `Uploading ${file.name}... (0%)`);

  const xhr = new XMLHttpRequest();
  xhr.open("POST", `${API_BASE_URL}${endpoint}`);

  // Track upload progress accurately
  xhr.upload.onprogress = (event) => {
    if (event.lengthComputable) {
      const percent = Math.round((event.loaded / event.total) * 100);
      if (percent < 100) {
        showProgress(percent, `Uploading ${file.name}... (${percent}%)`);
      } else {
        // 100% upload reached, now waiting for server NLP processing
        showProgress(100, "Processing summary on backend...");
        if (progressBar) progressBar.classList.add("processing");
      }
    }
  };

  xhr.onload = () => {
    stopLoading();
    hideProgress();

    if (xhr.status >= 200 && xhr.status < 300) {
      try {
        const data = JSON.parse(xhr.responseText);
        renderSummaryResult(data.summary, originalSize, data.filename || file.name);
        notifyToast("Summary generated successfully");
      } catch {
        const msg = "Invalid JSON response from server.";
        showError(msg);
        notifyToast(msg);
      }
    } else {
      const msg = parseXhrError(xhr);
      showError(msg);
      notifyToast(msg);
    }
  };

  xhr.onerror = () => {
    stopLoading();
    hideProgress();
    const msg = "Network error. Failed to reach backend.";
    showError(msg);
    notifyToast(msg);
  };

  xhr.send(formData);
}

function showProgress(percent, statusMsg) {
  if (uploadProgressBox) uploadProgressBox.classList.remove("hidden");
  if (progressBar) {
    progressBar.style.width = `${percent}%`;
    if (percent < 100) {
      progressBar.classList.remove("processing");
    }
  }
  if (progressPercent) progressPercent.textContent = `${percent}%`;
  if (progressStatus) progressStatus.textContent = statusMsg;
}

function hideProgress() {
  if (uploadProgressBox) uploadProgressBox.classList.add("hidden");
  if (progressBar) {
    progressBar.style.width = "0%";
    progressBar.classList.remove("processing");
  }
}

// --------------------------------------------------------------------------
// 11. Error Extraction & Presentation
// --------------------------------------------------------------------------

function parseXhrError(xhr) {
  try {
    const data = JSON.parse(xhr.responseText);
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail) && data.detail.length > 0) {
      return data.detail[0].msg || "Server validation error.";
    }
    return `Server error (${xhr.status}).`;
  } catch {
    return `Server error (${xhr.status}).`;
  }
}

async function extractErrorDetail(response) {
  try {
    const data = await response.json();
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail) && data.detail.length > 0) {
      return data.detail[0].msg || "Server validation error.";
    }
    return "Failed to generate summary.";
  } catch {
    return "Failed to connect to backend server.";
  }
}

function showError(msg) {
  if (errorMessage) {
    errorMessage.textContent = msg;
    errorMessage.classList.remove("hidden");
  }
}

function clearError() {
  if (errorMessage) {
    errorMessage.textContent = "";
    errorMessage.classList.add("hidden");
  }
}

// --------------------------------------------------------------------------
// 12. Result Presentation & XSS Safeguard
// --------------------------------------------------------------------------

function startLoading() {
  if (summarizeBtn) {
    summarizeBtn.disabled = true;
    summarizeBtn.innerHTML = '<span class="spinner" aria-hidden="true"></span>Summarizing...';
  }
  clearError();
}

function stopLoading() {
  if (summarizeBtn) {
    summarizeBtn.disabled = false;
    summarizeBtn.textContent = "✨ \u00a0 Generate summary";
  }
}

function renderSummaryResult(summary, originalCount, sourceLabel) {
  if (!summaryResult) return;

  // STRICT DOM-based XSS Prevention: innerText prevents script execution
  summaryResult.innerText = summary || "";

  if (emptyState) emptyState.style.display = "none";
  if (resultCard) resultCard.classList.add("show");

  if (resultStatus) {
    resultStatus.textContent = sourceLabel
      ? `●  Summary generated for ${sourceLabel}`
      : "●  Summary generated";
  }

  // Populate Statistics
  const orig = originalCount || summary.length;
  const summ = summary.length;
  const reductionPct = Math.max(0, Math.round((1 - summ / Math.max(orig, 1)) * 100));

  if (originalStat) originalStat.textContent = orig.toLocaleString();
  if (summarizedStat) summarizedStat.textContent = summ.toLocaleString();
  if (reductionStat) reductionStat.textContent = `${reductionPct}%`;
}

// --------------------------------------------------------------------------
// 13. Copy Summary to Clipboard
// --------------------------------------------------------------------------

if (copySummaryBtn) {
  copySummaryBtn.addEventListener("click", async () => {
    if (!summaryResult) return;
    const textToCopy = summaryResult.innerText.trim();

    if (!textToCopy) {
      notifyToast("No summary to copy.");
      return;
    }

    let success = false;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try {
        await navigator.clipboard.writeText(textToCopy);
        success = true;
      } catch {
        success = fallbackCopy(textToCopy);
      }
    } else {
      success = fallbackCopy(textToCopy);
    }

    if (success) {
      copySummaryBtn.classList.add("copied");
      copySummaryBtn.textContent = "Copied!";
      notifyToast("Summary copied");

      setTimeout(() => {
        copySummaryBtn.classList.remove("copied");
        copySummaryBtn.textContent = "Copy summary";
      }, 2000);
    } else {
      notifyToast("Clipboard permission unavailable");
    }
  });
}

function fallbackCopy(text) {
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.style.position = "fixed";
  ta.style.top = "0";
  ta.style.left = "0";
  ta.style.opacity = "0";
  document.body.appendChild(ta);
  ta.focus();
  ta.select();

  let successful = false;
  try {
    successful = document.execCommand("copy");
  } catch {
    successful = false;
  }

  document.body.removeChild(ta);
  return successful;
}

// --------------------------------------------------------------------------
// 14. Toast Notification System
// --------------------------------------------------------------------------

let toastTimeout = null;

function notifyToast(message) {
  if (!toastNotification) return;

  toastNotification.textContent = message;
  toastNotification.classList.add("show");

  if (toastTimeout) {
    clearTimeout(toastTimeout);
  }

  toastTimeout = setTimeout(() => {
    toastNotification.classList.remove("show");
  }, 2300);
}
