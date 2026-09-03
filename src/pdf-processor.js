import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";
import pdfWorkerUrl from "pdfjs-dist/legacy/build/pdf.worker.mjs?url";
import { processLabels as process } from "./pdf-core.js";

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

export function processLabels(sourceBytes, auxiliaryMode) {
  return process(sourceBytes, auxiliaryMode, pdfjsLib.getDocument);
}
