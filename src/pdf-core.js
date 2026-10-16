import { PDFDict, PDFDocument, PDFName } from "pdf-lib";

const A4_LANDSCAPE = [841.89, 595.276];
const LABEL_MARKER = /recort[aá]\s+esta\s+parte\s+de\s+la\s+etiqueta/i;
const FULL_LABEL_MARKER = /entregar\s+a\s+colecta\s+full/i;
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
    if (isHorizontal && (LABEL_MARKER.test(item.str || "") || FULL_LABEL_MARKER.test(item.str || ""))) {
      labels.add(clamp(Math.floor(item.transform[4] / (width / 3)), 0, 2));
    }
  }
  const text = textFromContent(content);
  const detected = [...labels].sort((a, b) => a - b).map((slot) => ({ slot }));
  // These templates have image logos, so recognize their textual fields together.
  // Anchor crops to a heading, allowing repeated labels and translated templates.
  const gestionar = /MARKETPLACE:/i.test(text) && /ID Envío:/i.test(text) && /Cobro Destino:/i.test(text);
  const correo = /F\.PAGADO/i.test(text) && /VENDEDOR/i.test(text) && /T&T\s+[A-Z]{2}\d+AR/i.test(text) && /DESTINATARIO/i.test(text);
  if (!detected.length && (gestionar || correo)) {
    for (const item of content.items) {
      const marker = gestionar ? /^Entrega Rápida$/i : /^REMITENTE$/;
      if (!marker.test(item.str || "") || Math.abs(item.transform[1]) > 0.01) continue;
      const scale = item.height / (gestionar ? 21.6 : 9);
      const x = item.transform[4];
      const y = item.transform[5];
      // Outer frame plus 1–2 pt padding, relative to the heading baseline.
      // Gestionar's A3 export: (33,172)-(319,809); Correo: (55,72)-(302,538).
      const offsets = gestionar
        ? [-62.401, -492.999, 223.599, 144.001]
        : [-10.1972, -322.159, 236.8028, 143.841];
      detected.push({ crop: {
        left: x + offsets[0] * scale, bottom: y + offsets[1] * scale,
        right: x + offsets[2] * scale, top: y + offsets[3] * scale
      } });
    }
  }
  return {
    labels: detected,
    hasCartDetail: CART_FOOTER.test(text),
    hasMeaningfulText: text.replace(/\s/g, "").length > 40
  };
}

function preparedLayout(source, classifications) {
  const labelPages = classifications.filter((page) => page.labels.length);
  if (!labelPages.length) return null;

  // pdf-lib writes each cropped label as an embedded page. PDF.js still exposes
  // text outside that crop, so text coordinates alone cannot identify the
  // generated layout reliably. Its page structure can: label pages contain one
  // or two embedded label pages, with an optional single one only at the end.
  const labelsPerPage = labelPages.map(({ pageIndex }) => {
    const resources = source.getPage(pageIndex).node.Resources();
    const xObjects = resources?.lookup(PDFName.of("XObject"), PDFDict);
    return xObjects
      ? [...xObjects.keys()].filter((name) => String(name).startsWith("/EmbeddedPdfPage-")).length
      : 0;
  });
  const valid = labelsPerPage.every((count, index) => count === 2 || (index === labelsPerPage.length - 1 && count === 1));
  if (!valid) return null;
  return { labels: labelsPerPage.reduce((total, count) => total + count, 0), sheets: labelsPerPage.length };
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
  const labels = classifications.flatMap((page) => page.labels.map((label) => ({ pageIndex: page.pageIndex, ...label })));
  if (!labels.length) throw new Error("No se encontraron etiquetas compatibles. Verificá que sea un PDF de etiquetas de Mercado Libre, Gestionar o Correo Argentino.");
  const source = await PDFDocument.load(sourceBytes.slice(0));
  const prepared = preparedLayout(source, classifications);
  if (prepared) {
    return {
      labels: prepared.labels,
      labelSheets: prepared.sheets,
      auxiliaryPages: classifications.filter((page) => page.includeAuxiliary).length,
      labelBytes: null,
      auxiliaryBytes: null,
      alreadyPrepared: true
    };
  }

  const output = await PDFDocument.create();
  output.setTitle("Etiquetas 2/3 A4");
  for (let index = 0; index < labels.length; index += 1) {
    const label = labels[index];
    const sourcePage = source.getPage(label.pageIndex);
    const { width, height } = sourcePage.getSize();
    const targetPage = index % 2 === 0 ? output.addPage(A4_LANDSCAPE) : output.getPage(output.getPageCount() - 1);
    const sourceFrame = label.crop || { ...labelFrame(width, label.slot), bottom: 0, top: height };
    // The recycled 2/3 sheet enters from the opposite side of the A4 page,
    // so its printable area corresponds to the two right-most label frames.
    const isUnpairedLastLabel = labels.length % 2 === 1 && index === labels.length - 1;
    const targetFrame = labelFrame(A4_LANDSCAPE[0], isUnpairedLastLabel ? 2 : (index % 2) + 1);
    const sourceLabel = await output.embedPage(sourcePage, {
      left: sourceFrame.left,
      bottom: sourceFrame.bottom,
      right: sourceFrame.right,
      top: sourceFrame.top
    });
    const cropWidth = sourceFrame.right - sourceFrame.left;
    const cropHeight = sourceFrame.top - sourceFrame.bottom;
    const scale = Math.min(targetFrame.width / cropWidth, A4_LANDSCAPE[1] / cropHeight);
    targetPage.drawPage(sourceLabel, {
      x: targetFrame.left + (targetFrame.width - cropWidth * scale) / 2,
      y: (A4_LANDSCAPE[1] - cropHeight * scale) / 2,
      width: cropWidth * scale, height: cropHeight * scale
    });
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
  return { labels: labels.length, labelSheets: Math.ceil(labels.length / 2), auxiliaryPages: auxiliaryPages.length, labelBytes: await output.save(), auxiliaryBytes, alreadyPrepared: false };
}
