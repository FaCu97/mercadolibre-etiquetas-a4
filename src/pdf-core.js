import { PDFDocument } from "pdf-lib";

const LABEL_MARKER = /recort[aá]\s+esta\s+parte\s+de\s+la\s+etiqueta/i;
const CART_FOOTER = /env[ií]e\s+sus\s+ventas\s+lo\s+antes\s+posible/i;
// Mercado Libre leaves unequal outer margins around its three visual labels.
// These ratios describe the actual label frames on its A4 landscape template,
// rather than treating the page as three mathematical thirds.
const LABEL_FRAME_STARTS = [0.037, 0.351, 0.665];
const LABEL_FRAME_WIDTH = 0.304;
const LABEL_FRAME_PADDING = 2;

function clamp(value, min, max) { return Math.max(min, Math.min(max, value)); }
function textFromContent(content) { return content.items.map((item) => item.str || "").join(" "); }

function labelFrame(pageWidth, slot) {
  const left = pageWidth * LABEL_FRAME_STARTS[slot] - LABEL_FRAME_PADDING;
  const right = pageWidth * (LABEL_FRAME_STARTS[slot] + LABEL_FRAME_WIDTH) + LABEL_FRAME_PADDING;
  return { left, right, width: right - left };
}

async function inspectPage(pdfPage) {
  const content = await pdfPage.getTextContent();
  const width = pdfPage.getViewport({ scale: 1 }).width;
  const labels = new Set();
  for (const item of content.items) {
    const isHorizontal = Math.abs(item.transform[0]) >= Math.abs(item.transform[1]);
    if (isHorizontal && LABEL_MARKER.test(item.str || "")) labels.add(clamp(Math.floor(item.transform[4] / (width / 3)), 0, 2));
  }
  const text = textFromContent(content);
  return {
    labels: [...labels].sort((a, b) => a - b),
    hasCartDetail: CART_FOOTER.test(text),
    hasMeaningfulText: text.replace(/\s/g, "").length > 40
  };
}

async function createAuxiliaryDocument(source, classifications) {
  const auxiliary = await PDFDocument.create();
  for (const item of classifications) {
    if (!item.includeAuxiliary) continue;
    const sourcePage = source.getPage(item.pageIndex);
    const { width, height } = sourcePage.getSize();
    if (item.hasCartDetail) {
      const page = auxiliary.addPage([width, height]);
      // Start after the label's actual right border, avoiding a sliver of label
      // in the cart-product document.
      // The vertical "Recortá…" instruction sits in the gap after the label.
      // Cart listings themselves start farther right in Mercado Libre's layout.
      const detailLeft = Math.max(labelFrame(width, 0).right, width * 0.44);
      // The list's natural content ends before the page edge. Crop that empty
      // margin and align its right edge with the fixed right edge of a label.
      const detailRight = width * 0.89;
      const detailWidth = detailRight - detailLeft;
      const targetRight = labelFrame(width, 2).right;
      const detail = await auxiliary.embedPage(sourcePage, { left: detailLeft, bottom: 0, right: detailRight, top: height });
      page.drawPage(detail, { x: targetRight - detailWidth, y: 0, width: detailWidth, height });
    } else {
      const [copied] = await auxiliary.copyPages(source, [item.pageIndex]);
      auxiliary.addPage(copied);
    }
  }
  return auxiliary;
}

export async function processLabels(sourceBytes, auxiliaryMode, getDocument) {
  const pdfjsDocument = await getDocument({ data: sourceBytes.slice(0) }).promise;
  const classifications = [];
  for (let pageIndex = 0; pageIndex < pdfjsDocument.numPages; pageIndex += 1) {
    const inspection = await inspectPage(await pdfjsDocument.getPage(pageIndex + 1));
    classifications.push({ pageIndex, ...inspection, includeAuxiliary: inspection.hasCartDetail || (!inspection.labels.length && inspection.hasMeaningfulText) });
  }
  await pdfjsDocument.destroy();
  const labels = classifications.flatMap((page) => page.labels.map((slot) => ({ pageIndex: page.pageIndex, slot })));
  if (!labels.length) throw new Error("No se encontraron etiquetas compatibles. Verificá que sea un PDF de etiquetas de Mercado Libre.");

  const source = await PDFDocument.load(sourceBytes.slice(0));
  const output = await PDFDocument.create();
  output.setTitle("Etiquetas 2/3 A4");
  for (let index = 0; index < labels.length; index += 1) {
    const label = labels[index];
    const sourcePage = source.getPage(label.pageIndex);
    const { width, height } = sourcePage.getSize();
    const targetPage = index % 2 === 0 ? output.addPage([width, height]) : output.getPage(output.getPageCount() - 1);
    const sourceFrame = labelFrame(width, label.slot);
    // The recycled 2/3 sheet enters from the opposite side of the A4 page,
    // so its printable area corresponds to the two right-most label frames.
    const isUnpairedLastLabel = labels.length % 2 === 1 && index === labels.length - 1;
    const targetFrame = labelFrame(width, isUnpairedLastLabel ? 2 : (index % 2) + 1);
    const sourceLabel = await output.embedPage(sourcePage, {
      left: sourceFrame.left,
      bottom: 0,
      right: sourceFrame.right,
      top: height
    });
    targetPage.drawPage(sourceLabel, { x: targetFrame.left, y: 0, width: targetFrame.width, height });
  }

  const auxiliaryPages = classifications.filter((page) => page.includeAuxiliary);
  let auxiliaryBytes = null;
  if (auxiliaryMode !== "discard" && auxiliaryPages.length) {
    const auxiliary = await createAuxiliaryDocument(source, classifications);
    if (auxiliaryMode === "combined") {
      const copied = await output.copyPages(auxiliary, auxiliary.getPageIndices());
      copied.forEach((page) => output.addPage(page));
    } else auxiliaryBytes = await auxiliary.save();
  }
  return { labels: labels.length, labelSheets: Math.ceil(labels.length / 2), auxiliaryPages: auxiliaryPages.length, labelBytes: await output.save(), auxiliaryBytes };
}
