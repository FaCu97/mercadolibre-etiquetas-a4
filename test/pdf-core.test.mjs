import assert from "node:assert/strict";
import fs from "node:fs/promises";
import test from "node:test";
import { PDFDocument } from "pdf-lib";
import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";
import { processLabels, processLabelFiles } from "../src/pdf-core.js";

const fixtureDirectory = "private-pdfs";
const fixturesAvailable = await fs.access(`${fixtureDirectory}/caso1.pdf`).then(() => true).catch(() => false);

async function run(fileName, mode) {
  return processLabels(new Uint8Array(await fs.readFile(`${fixtureDirectory}/${fileName}`)), mode, pdfjsLib.getDocument);
}

test("reorganiza los ejemplos privados de etiquetas", { skip: !fixturesAvailable }, async () => {
  for (const [file, labels, sheets] of [["caso1.pdf", 1, 1], ["caso2.pdf", 2, 1], ["caso3.pdf", 3, 2], ["caso4.pdf", 7, 4], ["caso5.pdf", 38, 19]]) {
    const output = await run(file, "discard");
    assert.equal(output.labels, labels, file);
    assert.equal(output.labelSheets, sheets, file);
    assert.equal((await PDFDocument.load(output.labelBytes)).getPageCount(), sheets, file);
  }
});

test("no vuelve a transformar un PDF ya preparado", { skip: !fixturesAvailable }, async () => {
  const firstPass = await run("caso3.pdf", "discard");
  const secondPass = await processLabels(firstPass.labelBytes, "discard", pdfjsLib.getDocument);
  assert.equal(secondPass.alreadyPrepared, true);
  assert.equal(secondPass.labels, 3);
  assert.equal(secondPass.labelSheets, 2);
  assert.equal(secondPass.labelBytes, null);
});

test("separa etiquetas, listados de carrito y control", { skip: !fixturesAvailable }, async () => {
  const output = await run("control.pdf", "separate");
  assert.equal(output.labels, 5);
  assert.equal(output.labelSheets, 3);
  assert.equal(output.auxiliaryPages, 3);
  assert.equal((await PDFDocument.load(output.labelBytes)).getPageCount(), 3);
  assert.equal((await PDFDocument.load(output.auxiliaryBytes)).getPageCount(), 3);
});

test("conserva todas las páginas de una hoja de control larga", { skip: !fixturesAvailable }, async () => {
  const output = await run("control2.pdf", "combined");
  assert.equal(output.labels, 38);
  assert.equal(output.labelSheets, 19);
  assert.equal(output.auxiliaryPages, 4);
  assert.equal((await PDFDocument.load(output.labelBytes)).getPageCount(), 23);
});

for (const file of ['caso6-gestionar.pdf', 'caso7-correoarg.pdf']) {
  const available = await fs.access(`${fixtureDirectory}/${file}`).then(() => true).catch(() => false);
  test(`adapta ${file} a A4 y reconoce el resultado`, { skip: !available }, async () => {
    const output = await run(file, 'separate');
    assert.equal(output.labels, 1);
    assert.equal(output.labelSheets, 1);
    assert.equal(output.auxiliaryPages, 0);
    assert.equal(output.auxiliaryBytes, null);
    const pdf = await PDFDocument.load(output.labelBytes);
    assert.equal(pdf.getPageCount(), 1);
    assert.ok(Math.abs(pdf.getPage(0).getWidth() - 841.89) < 0.01);
    assert.ok(Math.abs(pdf.getPage(0).getHeight() - 595.276) < 0.01);
    const second = await processLabels(output.labelBytes, 'discard', pdfjsLib.getDocument);
    assert.equal(second.alreadyPrepared, true);
    assert.equal(second.labels, 1);
  });
}

test('combina formatos distintos sin duplicar etiquetas ni crear auxiliares', { skip: !fixturesAvailable }, async (t) => {
  const files = ['caso1.pdf', 'caso6-gestionar.pdf', 'caso7-correoarg.pdf'];
  if (!(await Promise.all(files.map(f => fs.access(`${fixtureDirectory}/${f}`).then(() => true).catch(() => false)))).every(Boolean)) return t.skip('Faltan ejemplos privados');
  const source = await PDFDocument.create();
  for (const file of files) {
    const input = await PDFDocument.load(await fs.readFile(`${fixtureDirectory}/${file}`));
    (await source.copyPages(input, input.getPageIndices())).forEach(p => source.addPage(p));
  }
  const output = await processLabels(await source.save(), 'combined', pdfjsLib.getDocument);
  assert.equal(output.labels, 3);
  assert.equal(output.labelSheets, 2);
  assert.equal(output.auxiliaryPages, 0);
  const second = await processLabels(output.labelBytes, 'discard', pdfjsLib.getDocument);
  assert.equal(second.alreadyPrepared, true);
  assert.equal(second.labels, 3);
});

const viaAvailable = await fs.access(`${fixtureDirectory}/caso8-viacargo.pdf`).then(() => true).catch(() => false);
test('Vía Cargo: seis etiquetas en dos hojas, orden y códigos conservados', { skip: !viaAvailable }, async () => {
  const output = await run('caso8-viacargo.pdf', 'separate');
  assert.equal(output.labels, 6);
  assert.equal(output.labelSheets, 2);
  assert.equal(output.auxiliaryPages, 0);
  assert.equal(output.auxiliaryBytes, null);
  const doc = await pdfjsLib.getDocument({ data: output.labelBytes.slice() }).promise;
  const codes = [];
  for (let i = 1; i <= doc.numPages; i++) {
    const content = await (await doc.getPage(i)).getTextContent();
    const items = content.items.filter(item => /^\d{26}$/.test(item.str));
    assert.equal(items.length, i === 1 ? 4 : 2);
    for (const item of items) {
      assert.ok(item.transform[4] > 841.89 / 3, 'fuera del tercio vacío');
      assert.ok(item.transform[4] + item.width < 841.89, 'dentro del borde derecho');
      codes.push(item.str);
    }
  }
  await doc.destroy();
  assert.equal(new Set(codes).size, 6);
  assert.deepEqual(codes.map(code => code.slice(-3)), ['001', '002', '003', '004', '005', '006']);
  const second = await processLabels(output.labelBytes, 'discard', pdfjsLib.getDocument);
  assert.equal(second.alreadyPrepared, true);
  assert.equal(second.labels, 6);
  assert.equal(second.labelSheets, 2);
});

test('agrupa PDF individuales de Vía Cargo y rechaza entradas incompatibles o preparadas', { skip: !viaAvailable }, async () => {
  const source = await PDFDocument.load(await fs.readFile(`${fixtureDirectory}/caso8-viacargo.pdf`));
  const files = [];
  for (const index of source.getPageIndices()) {
    const single = await PDFDocument.create();
    const [page] = await single.copyPages(source, [index]);
    single.addPage(page);
    files.push(await single.save());
  }
  for (const count of [1, 2, 3, 4, 5, 6]) {
    const output = await processLabelFiles(files.slice(0, count), 'discard', pdfjsLib.getDocument);
    assert.equal(output.labels, count);
    assert.equal(output.labelSheets, Math.ceil(count / 4));
    const second = await processLabels(output.labelBytes, 'discard', pdfjsLib.getDocument);
    assert.equal(second.alreadyPrepared, true);
    assert.equal(second.labels, count);
  }
  const output = await processLabelFiles(files, 'discard', pdfjsLib.getDocument);
  await assert.rejects(processLabelFiles([files[0], output.labelBytes], 'discard', pdfjsLib.getDocument), /PDF 2 ya está preparado/);
  const blank = await PDFDocument.create();
  blank.addPage();
  await assert.rejects(processLabelFiles([files[0], await blank.save()], 'discard', pdfjsLib.getDocument), /PDF 2 no contiene/);
});

test('alterna etiquetas altas y compactas sin superponerlas', { skip: !viaAvailable || !fixturesAvailable }, async () => {
  const files = await Promise.all(['caso1.pdf', 'caso8-viacargo.pdf', 'caso1.pdf'].map(async file => new Uint8Array(await fs.readFile(`${fixtureDirectory}/${file}`))));
  const output = await processLabelFiles(files, 'discard', pdfjsLib.getDocument);
  assert.equal(output.labels, 8);
  assert.equal(output.labelSheets, 4);
  const second = await processLabels(output.labelBytes, 'discard', pdfjsLib.getDocument);
  assert.equal(second.alreadyPrepared, true);
  assert.equal(second.labels, 8);
  assert.equal(second.labelSheets, 4);
});
