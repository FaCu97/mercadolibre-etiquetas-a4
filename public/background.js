function pdfSource(url) {
  try {
    const tab = new URL(url);
    const source = tab.protocol === "file:" ? tab.href : tab.searchParams.get("file");
    return source && new URL(source).protocol === "file:" ? source : null;
  } catch { return null; }
}

async function setActionForTab(tab) {
  if (!tab?.id) return;
  await chrome.action.setPopup({ tabId: tab.id, popup: pdfSource(tab.url) ? "" : "app.html" });
}

async function setActionForActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  await setActionForTab(tab);
}

chrome.tabs.onActivated.addListener(setActionForActiveTab);
chrome.tabs.onUpdated.addListener((_tabId, changeInfo, tab) => {
  if (changeInfo.url || changeInfo.status === "complete") setActionForTab(tab);
});
chrome.runtime.onStartup.addListener(setActionForActiveTab);

let creatingOffscreen;
async function ensureOffscreenDocument() {
  const contexts = await chrome.runtime.getContexts({ contextTypes: ["OFFSCREEN_DOCUMENT"], documentUrls: [chrome.runtime.getURL("offscreen.html")] });
  if (contexts.length) return;
  if (!creatingOffscreen) {
    creatingOffscreen = chrome.offscreen.createDocument({
      url: "offscreen.html",
      reasons: ["BLOBS"],
      justification: "Procesar el PDF abierto y descargar los archivos resultantes sin mostrar una pestaña."
    }).finally(() => { creatingOffscreen = null; });
  }
  await creatingOffscreen;
}

const defaultTitle = "Preparar etiquetas para hoja 2/3 A4";
function showResult(text, color, title = defaultTitle) {
  chrome.action.setBadgeBackgroundColor({ color });
  chrome.action.setBadgeText({ text });
  chrome.action.setTitle({ title });
  setTimeout(() => {
    chrome.action.setBadgeText({ text: "" });
    chrome.action.setTitle({ title: defaultTitle });
  }, 10_000);
}

chrome.action.onClicked.addListener(async (tab) => {
  const source = pdfSource(tab.url);
  if (!source) return;
  const allowed = await new Promise((resolve) => chrome.extension.isAllowedFileSchemeAccess(resolve));
  if (!allowed) return showResult("!", "#b42318", "Activá el acceso a URLs de archivos en los detalles de la extensión.");
  try {
    await ensureOffscreenDocument();
    showResult("…", "#3483fa");
    const { auxiliaryMode } = await chrome.storage.local.get({ auxiliaryMode: "discard" });
    chrome.runtime.sendMessage({ type: "process-active-pdf", source, auxiliaryMode });
  } catch (error) {
    showResult("!", "#b42318", error.message || "No se pudo iniciar el procesamiento.");
  }
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "pdf-ready-for-download") {
    Promise.all(message.files.map((file) => chrome.downloads.download({
      url: file.url,
      filename: file.filename,
      saveAs: false
    }))).then(() => {
      showResult("✓", "#16784b");
      sendResponse({ ok: true });
    }).catch((error) => {
      console.error("No se pudo iniciar la descarga", error);
      showResult("!", "#b42318", `No se pudo descargar el PDF: ${error.message || "error desconocido"}`);
      sendResponse({ ok: false });
    });
    return true;
  }
  if (message.type === "pdf-processed") showResult("✓", "#16784b");
  if (message.type === "pdf-already-prepared") {
    showResult("YA", "#16784b", "El PDF ya estaba preparado para imprimir.");
  }
  if (message.type === "pdf-failed") showResult("!", "#b42318", message.reason || "No se pudo procesar el PDF.");
});

setActionForActiveTab();
