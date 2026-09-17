import { useEffect, useState } from "react";
import {
  CaretLeft,
  CaretRight,
  FilePdf,
  ImageSquare,
  ShieldCheck,
} from "@phosphor-icons/react";
import Markdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import type {
  ArtifactDocument,
  PdfTextArtifactDocument,
  TextArtifactDocument,
} from "../types";

interface DocumentRendererProps {
  document: ArtifactDocument;
}

function splitFrontmatter(source: string) {
  const normalized = source.replaceAll("\r\n", "\n");
  if (!normalized.startsWith("---\n")) {
    return { frontmatter: null, body: source };
  }
  const closing = normalized.indexOf("\n---\n", 4);
  if (closing === -1) {
    return { frontmatter: null, body: source };
  }
  return {
    frontmatter: normalized.slice(4, closing),
    body: normalized.slice(closing + 5),
  };
}

function safeLink(href: string | undefined) {
  if (!href) return null;
  if (href.startsWith("#")) return href;
  try {
    const parsed = new URL(href);
    return ["https:", "http:", "mailto:"].includes(parsed.protocol)
      ? href
      : null;
  } catch {
    return null;
  }
}

const markdownComponents: Components = {
  a({ node: _node, href, children, ...props }) {
    const safeHref = safeLink(href);
    if (!safeHref) {
      return (
        <span className="document-link--unavailable" title="Link omitted from safety preview">
          {children}
        </span>
      );
    }
    const external = !safeHref.startsWith("#");
    return (
      <a
        {...props}
        href={safeHref}
        {...(external
          ? { target: "_blank", rel: "noreferrer noopener" }
          : {})}
      >
        {children}
      </a>
    );
  },
  img({ node: _node, alt }) {
    return (
      <span className="document-media-omitted" role="note">
        <ImageSquare aria-hidden="true" />
        {alt ? `Image omitted: ${alt}` : "Image omitted from safety preview"}
      </span>
    );
  },
  pre({ node: _node, children, ...props }) {
    return (
      <pre {...props} className="document-code-block" tabIndex={0}>
        {children}
      </pre>
    );
  },
  table({ node: _node, children, ...props }) {
    return (
      <div
        className="document-table-scroll"
        role="region"
        aria-label="Scrollable document table"
        tabIndex={0}
      >
        <table {...props}>{children}</table>
      </div>
    );
  },
};

function MarkdownDocument({ document }: { document: TextArtifactDocument }) {
  const { frontmatter, body } = splitFrontmatter(document.content);
  return (
    <article className="document-reader markdown-document" aria-label="Markdown document">
      {frontmatter ? (
        <details className="document-frontmatter">
          <summary>Document metadata</summary>
          <pre tabIndex={0}>{frontmatter}</pre>
        </details>
      ) : null}
      <Markdown
        remarkPlugins={[remarkGfm]}
        components={markdownComponents}
        skipHtml
      >
        {body}
      </Markdown>
    </article>
  );
}

function PlainTextDocument({ document }: { document: TextArtifactDocument }) {
  return (
    <pre className="document-reader document-plain-text" tabIndex={0}>
      {document.content}
    </pre>
  );
}

function PdfTextDocument({ document }: { document: PdfTextArtifactDocument }) {
  const [pageIndex, setPageIndex] = useState(0);
  useEffect(() => setPageIndex(0), [document.path, document.sha256]);

  const textPages = document.pages.filter((page) => page.text.trim().length > 0);
  const page = textPages[Math.min(pageIndex, Math.max(textPages.length - 1, 0))];

  if (!page) {
    return (
      <div className="document-reader pdf-text-reader pdf-text-reader--empty" role="status">
        <FilePdf size={28} aria-hidden="true" />
        <strong>No extractable text</strong>
        <p>
          This PDF may contain only images or outlined text. Its verified source
          remains attached to the snapshot, but the bridge will not expose raw
          PDF bytes.
        </p>
      </div>
    );
  }

  return (
    <section className="document-reader pdf-text-reader" aria-label="PDF text preview">
      <div className="pdf-text-reader__notice" role="note">
        <ShieldCheck weight="fill" aria-hidden="true" />
        <span>
          <strong>Safety preview</strong>
          Redacted page text only. Visual layout, images, links, and attachments
          are omitted.
        </span>
      </div>

      <nav className="pdf-text-reader__controls" aria-label="PDF page navigation">
        <button
          type="button"
          onClick={() => setPageIndex((current) => Math.max(0, current - 1))}
          disabled={pageIndex === 0}
          aria-label="Previous PDF page"
        >
          <CaretLeft aria-hidden="true" />
          Previous
        </button>
        <span aria-live="polite">
          Page {page.number} of {document.pageCount}
        </span>
        <button
          type="button"
          onClick={() =>
            setPageIndex((current) => Math.min(textPages.length - 1, current + 1))
          }
          disabled={pageIndex >= textPages.length - 1}
          aria-label="Next PDF page"
        >
          Next
          <CaretRight aria-hidden="true" />
        </button>
      </nav>

      <article className="pdf-text-page" aria-labelledby="pdf-text-page-title">
        <header>
          <FilePdf aria-hidden="true" />
          <h2 id="pdf-text-page-title">Page {page.number}</h2>
        </header>
        <div>{page.text}</div>
      </article>
    </section>
  );
}

export function DocumentRenderer({ document }: DocumentRendererProps) {
  if (document.format === "markdown") {
    return <MarkdownDocument document={document} />;
  }
  if (document.format === "pdf-text") {
    return <PdfTextDocument document={document} />;
  }
  return <PlainTextDocument document={document} />;
}
