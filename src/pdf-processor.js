import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";
import pdfWorkerUrl from "pdfjs-dist/legacy/build/pdf.worker.mjs?url";
import { processLabels as process, processLabelFiles as processFiles } from "./pdf-core.js";

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

export function processLabels(sourceBytes, auxiliaryMode) {
  return process(sourceBytes, auxiliaryMode, pdfjsLib.getDocument);
}

export function processLabelFiles(files, auxiliaryMode) {
  return processFiles(files, auxiliaryMode, pdfjsLib.getDocument);
}
