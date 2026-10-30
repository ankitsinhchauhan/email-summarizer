// DOM Elements
const textTab = document.getElementById("textTab");
const txtTab = document.getElementById("txtTab");
const pdfTab = document.getElementById("pdfTab");

const textPanel = document.getElementById("textPanel");
const txtPanel = document.getElementById("txtPanel");
const pdfPanel = document.getElementById("pdfPanel");

const inputText = document.getElementById("inputText");
const charCount = document.getElementById("charCount");

const txtFileInput = document.getElementById("txtFileInput");
const txtFileInfo = document.getElementById("txtFileInfo");
const txtRemoveBtn = document.getElementById("txtRemoveBtn");

const pdfFileInput = document.getElementById("pdfFileInput");
const pdfFileInfo = document.getElementById("pdfFileInfo");
const pdfRemoveBtn = document.getElementById("pdfRemoveBtn");

const maxLengthInput = document.getElementById("maxLength");
const minLengthInput = document.getElementById("minLength");

const summarizeBtn = document.getElementById("summarizeBtn");
const spinner = document.getElementById("spinner");
const summaryBox = document.getElementById("summaryBox");
const summaryResult = document.getElementById("summaryResult");
const errorMessage = document.getElementById("errorMessage");
const themeToggle = document.getElementById("themeToggle");

// Environment-aware API Base URL
const isLocalhost =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1" ||
  window.location.hostname === "";

const API_BASE_URL = isLocalhost
  ? "http://127.0.0.1:8000"
  : "https://email-summarizer-api-3x50.onrender.com";

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

// Tab Mode: "text" | "txt" | "pdf"
let activeMode = localStorage.getItem("activeMode") || "text";
if (!["text", "txt", "pdf"].includes(activeMode)) {
  activeMode = "text";
}

setActiveMode(activeMode);
loadSavedTheme();

// Event Listeners: Input & Theme
inputText.addEventListener("input", () => {
  charCount.innerText = `${inputText.value.length} characters`;
  clearMessage();
});

themeToggle.addEventListener("click", () => {
  const html = document.documentElement;
  const currentTheme = html.getAttribute("data-theme");

  if (currentTheme === "dark") {
    html.setAttribute("data-theme", "light");
    themeToggle.innerText = "☀️ Light Mode";
    localStorage.setItem("theme", "light");
  } else {
    html.setAttribute("data-theme", "dark");
    themeToggle.innerText = "🌙 Dark Mode";
    localStorage.setItem("theme", "dark");
  }
});

// Event Listeners: Tabs
textTab.addEventListener("click", () => setActiveMode("text"));
txtTab.addEventListener("click", () => setActiveMode("txt"));
pdfTab.addEventListener("click", () => setActiveMode("pdf"));

// Event Listeners: TXT File Input & Remove
txtFileInput.addEventListener("change", () => {
  clearMessage();
  if (txtFileInput.files && txtFileInput.files.length > 0) {
    const file = txtFileInput.files[0];
    if (!file.name.toLowerCase().endsWith(".txt")) {
      showError("Please select a valid plain text (.txt) file.");
      txtFileInput.value = "";
      txtFileInfo.innerText = "No file selected";
      txtRemoveBtn.classList.add("hidden");
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      showError("File is too large. Maximum allowed size is 10 MB.");
      txtFileInput.value = "";
      txtFileInfo.innerText = "No file selected";
      txtRemoveBtn.classList.add("hidden");
      return;
    }
    txtFileInfo.innerText = `📄 ${file.name} (${formatFileSize(file.size)})`;
    txtRemoveBtn.classList.remove("hidden");
  } else {
    txtFileInfo.innerText = "No file selected";
    txtRemoveBtn.classList.add("hidden");
  }
});

txtRemoveBtn.addEventListener("click", () => {
  txtFileInput.value = "";
  txtFileInfo.innerText = "No file selected";
  txtRemoveBtn.classList.add("hidden");
  clearMessage();
});

// Event Listeners: PDF File Input & Remove
pdfFileInput.addEventListener("change", () => {
  clearMessage();
  if (pdfFileInput.files && pdfFileInput.files.length > 0) {
    const file = pdfFileInput.files[0];
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      showError("Please select a valid PDF (.pdf) file.");
      pdfFileInput.value = "";
      pdfFileInfo.innerText = "No file selected";
      pdfRemoveBtn.classList.add("hidden");
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      showError("PDF file is too large. Maximum allowed size is 10 MB.");
      pdfFileInput.value = "";
      pdfFileInfo.innerText = "No file selected";
      pdfRemoveBtn.classList.add("hidden");
      return;
    }
    pdfFileInfo.innerText = `📕 ${file.name} (${formatFileSize(file.size)})`;
    pdfRemoveBtn.classList.remove("hidden");
  } else {
    pdfFileInfo.innerText = "No file selected";
    pdfRemoveBtn.classList.add("hidden");
  }
});

pdfRemoveBtn.addEventListener("click", () => {
  pdfFileInput.value = "";
  pdfFileInfo.innerText = "No file selected";
  pdfRemoveBtn.classList.add("hidden");
  clearMessage();
});

// Event Listener: Summarize Action
summarizeBtn.addEventListener("click", async () => {
  if (activeMode === "text") {
    await summarizeText();
  } else if (activeMode === "txt") {
    await summarizeTxtFile();
  } else if (activeMode === "pdf") {
    await summarizePdfFile();
  }
});

function setActiveMode(mode) {
  activeMode = mode;
  localStorage.setItem("activeMode", mode);

  // Reset tab active states & ARIA
  [textTab, txtTab, pdfTab].forEach((tab) => {
    tab.classList.remove("active");
    tab.setAttribute("aria-selected", "false");
  });
  [textPanel, txtPanel, pdfPanel].forEach((panel) => panel.classList.add("hidden"));

  if (mode === "text") {
    textTab.classList.add("active");
    textTab.setAttribute("aria-selected", "true");
    textPanel.classList.remove("hidden");
  } else if (mode === "txt") {
    txtTab.classList.add("active");
    txtTab.setAttribute("aria-selected", "true");
    txtPanel.classList.remove("hidden");
  } else if (mode === "pdf") {
    pdfTab.classList.add("active");
    pdfTab.setAttribute("aria-selected", "true");
    pdfPanel.classList.remove("hidden");
  }

  clearMessage();
}

function loadSavedTheme() {
  const savedTheme = localStorage.getItem("theme") || "dark";
  const html = document.documentElement;

  html.setAttribute("data-theme", savedTheme);

  if (savedTheme === "light") {
    themeToggle.innerText = "☀️ Light Mode";
  } else {
    themeToggle.innerText = "🌙 Dark Mode";
  }
}

// Text Summarization
async function summarizeText() {
  const text = inputText.value.trim();
  const maxLength = getMaxLength();
  const minLength = getMinLength();

  if (!validateLengths(minLength, maxLength)) return;

  if (text.length < 200) {
    showError("Please enter at least 200 characters.");
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
        max_length: maxLength,
        min_length: minLength,
      }),
    });

    if (!response.ok) {
      throw new Error(await getResponseError(response));
    }

    const data = await response.json();
    showSummary(data.summary);
    showSuccess("Summary generated successfully.");
  } catch (error) {
    showError(error.message);
    showPlaceholder("Something went wrong. Try again.");
  } finally {
    stopLoading();
  }
}

// TXT File Summarization
async function summarizeTxtFile() {
  const file = txtFileInput.files ? txtFileInput.files[0] : null;
  const maxLength = getMaxLength();
  const minLength = getMinLength();

  if (!validateLengths(minLength, maxLength)) return;

  if (!file) {
    showError("Please select a .txt file first.");
    return;
  }

  if (!file.name.toLowerCase().endsWith(".txt")) {
    showError("Only plain text (.txt) files are supported.");
    return;
  }

  if (file.size > MAX_FILE_SIZE) {
    showError("File is too large. Maximum allowed size is 10 MB.");
    return;
  }

  await uploadAndSummarize(file, maxLength, minLength, "/summarize-file");
}

// PDF File Summarization
async function summarizePdfFile() {
  const file = pdfFileInput.files ? pdfFileInput.files[0] : null;
  const maxLength = getMaxLength();
  const minLength = getMinLength();

  if (!validateLengths(minLength, maxLength)) return;

  if (!file) {
    showError("Please select a .pdf file first.");
    return;
  }

  if (!file.name.toLowerCase().endsWith(".pdf")) {
    showError("Only PDF (.pdf) documents are supported.");
    return;
  }

  if (file.size > MAX_FILE_SIZE) {
    showError("PDF file is too large. Maximum allowed size is 10 MB.");
    return;
  }

  await uploadAndSummarize(file, maxLength, minLength, "/summarize-pdf");
}

// Generic Multipart Upload
async function uploadAndSummarize(file, maxLength, minLength, endpoint) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("max_length", maxLength);
  formData.append("min_length", minLength);

  startLoading();

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(await getResponseError(response));
    }

    const data = await response.json();
    showSummary(data.summary);
    showSuccess(`Summary of "${data.filename || file.name}" generated successfully.`);
  } catch (error) {
    showError(error.message);
    showPlaceholder("Could not generate summary. Please check the error above.");
  } finally {
    stopLoading();
  }
}

// Error Extraction Helper
async function getResponseError(response) {
  try {
    const data = await response.json();
    if (typeof data.detail === "string") {
      return data.detail;
    }
    if (Array.isArray(data.detail) && data.detail.length > 0) {
      return data.detail[0].msg || "Validation error on server.";
    }
    return "Server error. Please check your FastAPI backend.";
  } catch (error) {
    return "Server error. Could not connect to backend.";
  }
}

function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getMaxLength() {
  return parseInt(maxLengthInput.value, 10);
}

function getMinLength() {
  return parseInt(minLengthInput.value, 10);
}

function validateLengths(minLength, maxLength) {
  clearMessage();

  if (Number.isNaN(minLength) || Number.isNaN(maxLength)) {
    showError("Please enter valid numeric summary lengths.");
    return false;
  }

  if (minLength < 10 || minLength > 150) {
    showError("Min length must be between 10 and 150.");
    return false;
  }

  if (maxLength < 50 || maxLength > 300) {
    showError("Max length must be between 50 and 300.");
    return false;
  }

  if (minLength >= maxLength) {
    showError("Min length must be smaller than max length.");
    return false;
  }

  return true;
}

function startLoading() {
  summarizeBtn.disabled = true;
  summarizeBtn.innerText = "Summarizing...";
  spinner.classList.add("show");
  summaryBox.classList.remove("active");
  showPlaceholder("Analyzing document and generating summary, please wait...");
}

function stopLoading() {
  summarizeBtn.disabled = false;
  summarizeBtn.innerText = "Generate Summary";
  spinner.classList.remove("show");
}

function showSummary(summary) {
  summaryResult.className = "";
  summaryResult.innerText = summary || "No summary received.";
  summaryBox.classList.add("active");
}

function showPlaceholder(message) {
  summaryResult.className = "muted";
  summaryResult.innerText = message;
}

function showError(message) {
  errorMessage.className = "error";
  errorMessage.innerText = message;
}

function showSuccess(message) {
  errorMessage.className = "error success";
  errorMessage.innerText = message;
}

function clearMessage() {
  errorMessage.className = "error";
  errorMessage.innerText = "";
}
