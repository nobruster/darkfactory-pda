import { getDocument } from "pdfjs-dist/legacy/build/pdf.mjs";

import { redactSensitiveTextWithReport } from "./security.mjs";

const DEFAULT_MAX_PAGES = 100;
const DEFAULT_MAX_TEXT_BYTES = 256 * 1024;

function pdfPreviewError(message, options = {}) {
  const error = new Error(message, options);
  error.code = "PDF_PREVIEW_INVALID";
  return error;
}

function hasPdfHeader(contents) {
  return contents.subarray(0, Math.min(contents.byteLength, 1024)).includes("%PDF-");
}

function textFromItems(items) {
  const parts = [];
  for (const item of items) {
    if (!item || typeof item.str !== "string") continue;
    parts.push(item.str);
    parts.push(item.hasEOL ? "\n" : " ");
  }
  return parts
    .join("")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function takeUtf8(value, maxBytes) {
  if (maxBytes <= 0) return "";
  if (Buffer.byteLength(value, "utf8") <= maxBytes) return value;

  let low = 0;
  let high = value.length;
  while (low < high) {
    const middle = Math.ceil((low + high) / 2);
    if (Buffer.byteLength(value.slice(0, middle), "utf8") <= maxBytes) {
      low = middle;
    } else {
      high = middle - 1;
    }
  }
  return value.slice(0, low);
}

export async function extractPdfText(
  contents,
  {
    maxPages = DEFAULT_MAX_PAGES,
    maxTextBytes = DEFAULT_MAX_TEXT_BYTES,
  } = {},
) {
  if (!Buffer.isBuffer(contents) || !hasPdfHeader(contents)) {
    throw pdfPreviewError("artifact does not contain a valid PDF header");
  }
  if (!Number.isInteger(maxPages) || maxPages < 1) {
    throw new TypeError("PDF preview maxPages must be a positive integer");
  }
  if (!Number.isInteger(maxTextBytes) || maxTextBytes < 1) {
    throw new TypeError("PDF preview maxTextBytes must be a positive integer");
  }

  let loadingTask;
  try {
    loadingTask = getDocument({
      data: new Uint8Array(contents),
      disableAutoFetch: true,
      disableStream: true,
      enableXfa: false,
      isEvalSupported: false,
      stopAtErrors: true,
      useSystemFonts: false,
      verbosity: 0,
    });
    const pdf = await loadingTask.promise;
    const pages = [];
    const pageLimit = Math.min(pdf.numPages, maxPages);
    let remainingBytes = maxTextBytes;
    let redacted = false;
    let truncated = pdf.numPages > pageLimit;

    for (let pageNumber = 1; pageNumber <= pageLimit; pageNumber += 1) {
      if (remainingBytes <= 0) {
        truncated = true;
        break;
      }
      const page = await pdf.getPage(pageNumber);
      const textContent = await page.getTextContent({
        disableNormalization: false,
        includeMarkedContent: false,
      });
      const result = redactSensitiveTextWithReport(
        textFromItems(textContent.items),
      );
      const pageText = takeUtf8(result.content, remainingBytes);
      const pageBytes = Buffer.byteLength(pageText, "utf8");
      pages.push({ number: pageNumber, text: pageText });
      remainingBytes -= pageBytes;
      redacted ||= result.redacted;
      if (pageText !== result.content) {
        truncated = true;
        break;
      }
    }

    return {
      pages,
      pageCount: pdf.numPages,
      redacted,
      truncated,
    };
  } catch (error) {
    if (error?.code === "PDF_PREVIEW_INVALID") throw error;
    throw pdfPreviewError("PDF text could not be extracted safely", {
      cause: error,
    });
  } finally {
    if (loadingTask) {
      try {
        await loadingTask.destroy();
      } catch {
        // The preview result is already detached from the parser task.
      }
    }
  }
}

export { DEFAULT_MAX_PAGES, DEFAULT_MAX_TEXT_BYTES };
