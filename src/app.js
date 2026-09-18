import "./style.css";
import { processLabels } from "./pdf-processor.js";

const fileInput = document.querySelector("#source-file");
const fileName = document.querySelector("#file-name");
const generateButton = document.querySelector("#generate");
const status = document.querySelector("#status");
const summary = document.querySelector("#summary");
const dropZone = document.querySelector("#drop-zone");
const modeLabel = document.querySelector("#mode-label");
const settingsStatus = document.querySelector("#settings-status");
const version = document.querySelector("#version");
const modeInputs = [...document.querySelectorAll('input[name="auxiliary-mode"]')];
const tabButtons = [...document.querySelectorAll("[data-panel]")];
const panels = [...document.querySelectorAll(".tab-panel")];
let selectedFile = null;

const stored = await chrome.storage.local.get({ auxiliaryMode: "discard" });
version.textContent = chrome.runtime.getManifest().version;
const modeNames = { discard: "descartar", separate: "archivo separado", combined: "mismo PDF" };
modeLabel.textContent = modeNames[stored.auxiliaryMode] || "descartar";
modeInputs.find((input) => input.value === stored.auxiliaryMode).checked = true;

function auxiliaryMode() { return stored.auxiliaryMode; }

function setStatus(message, type = "") {
  status.textContent = message;
  status.className = `status ${type}`;
}

function openPanel(panelId) {
  panels.forEach((panel) => { panel.hidden = panel.id !== panelId; });
  tabButtons.forEach((button) => {
    const active = button.dataset.panel === panelId;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-selected", String(active));
  });
  if (panelId === "settings-panel") settingsStatus.textContent = "";
}

tabButtons.forEach((button) => button.addEventListener("click", () => openPanel(button.dataset.panel)));

modeInputs.forEach((input) => input.addEventListener("change", async () => {
  stored.auxiliaryMode = input.value;
  await chrome.storage.local.set({ auxiliaryMode: input.value });
  modeLabel.textContent = modeNames[input.value];
  settingsStatus.textContent = "Configuración guardada.";
}));

function setFile(file) {
  if (!file || file.type !== "application/pdf") {
    setStatus("Elegí un archivo PDF.", "error");
    return;
  }
  selectedFile = file;
  fileName.textContent = file.name;
  summary.textContent = "Listo para analizar y reacomodar las etiquetas.";
  generateButton.disabled = false;
  setStatus("");
}

function download(bytes, filename) {
  const url = URL.createObjectURL(new Blob([bytes], { type: "application/pdf" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

fileInput.addEventListener("change", () => setFile(fileInput.files[0]));
for (const eventName of ["dragenter", "dragover"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("dragging");
  });
}
for (const eventName of ["dragleave", "drop"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("dragging");
  });
}
dropZone.addEventListener("drop", (event) => setFile(event.dataTransfer.files[0]));

generateButton.addEventListener("click", async () => {
  if (!selectedFile) return;
  generateButton.disabled = true;
  setStatus("Analizando y generando PDFs…");
  try {
    const output = await processLabels(new Uint8Array(await selectedFile.arrayBuffer()), auxiliaryMode());
    const baseName = selectedFile.name.replace(/\.pdf$/i, "");
    download(output.labelBytes, `${baseName}-etiquetas-2-tercios.pdf`);
    if (output.auxiliaryBytes) download(output.auxiliaryBytes, `${baseName}-documentos-auxiliares.pdf`);
    summary.textContent = `${output.labels} etiquetas en ${output.labelSheets} hoja${output.labelSheets === 1 ? "" : "s"} A4.`;
    setStatus(
      output.auxiliaryPages
        ? `Listo. También se detectaron ${output.auxiliaryPages} página${output.auxiliaryPages === 1 ? "" : "s"} auxiliar${output.auxiliaryPages === 1 ? "" : "es"}.`
        : "Listo. No se detectaron documentos auxiliares.",
      "success"
    );
  } catch (error) {
    console.error(error);
    setStatus(error.message || "No se pudo procesar el PDF.", "error");
  } finally {
    generateButton.disabled = false;
  }
});

const query = new URLSearchParams(location.search);
if (query.has("fileAccess")) setStatus("Activá “Permitir acceso a URLs de archivos” en chrome://extensions para usar la conversión con un clic.", "error");

function pdfSource(url) {
  try {
    const tab = new URL(url);
    const source = tab.protocol === "file:" ? tab.href : tab.searchParams.get("file");
    return source && new URL(source).protocol === "file:" ? source : null;
  } catch {
    return null;
  }
}

async function openSource(source) {
  try {
    setStatus("Convirtiendo el PDF abierto…");
    const response = await fetch(source);
    const name = decodeURIComponent(new URL(source).pathname.split("/").pop() || "etiquetas.pdf");
    setFile(new File([await response.blob()], name, { type: "application/pdf" }));
    generateButton.click();
  } catch { setStatus("No se pudo leer el PDF abierto. Verificá el permiso de archivos locales.", "error"); }
}

async function processActivePdf() {
  const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  const source = pdfSource(tab?.url);
  if (!source) return;

  const allowed = await new Promise((resolve) => chrome.extension.isAllowedFileSchemeAccess(resolve));
  if (!allowed) {
    setStatus("Activá “Permitir acceso a URLs de archivos” en chrome://extensions para convertir el PDF abierto.", "error");
    return;
  }
  await openSource(source);
}

if (query.has("source")) openSource(query.get("source"));
else if (!query.has("fileAccess")) processActivePdf();
