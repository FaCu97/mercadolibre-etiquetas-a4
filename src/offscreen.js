import { processLabels } from "./pdf-processor.js";

function prepareDownload(bytes, filename) {
  let binary = "";
  const chunkSize = 0x8000;
  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + chunkSize));
  }
  return { url: `data:application/pdf;base64,${btoa(binary)}`, filename };
}

chrome.runtime.onMessage.addListener((message) => {
  if (message.type !== "process-active-pdf") return;
  (async () => {
    try {
      const response = await fetch(message.source);
      const name = decodeURIComponent(new URL(message.source).pathname.split("/").pop() || "etiquetas.pdf");
      const baseName = name.replace(/\.pdf$/i, "");
      const output = await processLabels(new Uint8Array(await response.arrayBuffer()), message.auxiliaryMode || "discard");
      const files = [prepareDownload(output.labelBytes, `${baseName}-etiquetas-2-tercios.pdf`)];
      if (output.auxiliaryBytes) files.push(prepareDownload(output.auxiliaryBytes, `${baseName}-documentos-auxiliares.pdf`));
      await chrome.runtime.sendMessage({ type: "pdf-ready-for-download", files });
    } catch (error) {
      console.error(error);
      chrome.runtime.sendMessage({ type: "pdf-failed", reason: error.message || "No se pudo procesar el PDF." });
    }
  })();
});
