import assert from "node:assert/strict";
import fs from "node:fs/promises";
import test from "node:test";
import { PDFDocument } from "pdf-lib";
import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";
import { processLabels } from "../src/pdf-core.js";

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
