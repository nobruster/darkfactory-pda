#!/usr/bin/env python3
"""Build the current composed v0.2 release PDF from canonical Markdown sources."""

from __future__ import annotations

import html
import pathlib
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfbase.pdfmetrics import stringWidth

ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
SOURCES = [ROOT / "README.md"]
OUTPUT = ROOT / "tmp" / "converge-release-guide.pdf"
MERMAID_DIR = ROOT / "tmp" / "pdfs" / "mermaid"
INK = colors.HexColor("#14231F")
GREEN = colors.HexColor("#176B56")
MINT = colors.HexColor("#DDF2EA")
GOLD = colors.HexColor("#C18A2B")
PAPER = colors.HexColor("#FAF8F2")
MUTED = colors.HexColor("#64736D")
LINE = colors.HexColor("#CAD8D2")


class SectionRule(Flowable):
    def __init__(self, color: colors.Color = GREEN):
        super().__init__()
        self.color = color
        self.height = 6

    def draw(self) -> None:
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(1.2)
        self.canv.line(0, 3, self._availWidth, 3)

    def wrap(self, avail_width: float, avail_height: float) -> tuple[float, float]:
        self._availWidth = avail_width
        return avail_width, self.height


def inline(value: str) -> str:
    value = html.escape(value.strip())
    value = re.sub(r"!\[([^]]*)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"\[([^]]+)\]\([^)]+\)", r"<u>\1</u>", value)
    value = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", value)
    return value


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("H1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=24, leading=29, textColor=INK, spaceBefore=12, spaceAfter=11),
        "h2": ParagraphStyle("H2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=GREEN, spaceBefore=14, spaceAfter=7, keepWithNext=True),
        "h3": ParagraphStyle("H3", parent=base["Heading3"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=INK, spaceBefore=10, spaceAfter=5, keepWithNext=True),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName="Helvetica", fontSize=8.9, leading=12.6, textColor=INK, spaceAfter=6),
        "bullet": ParagraphStyle("Bullet", parent=base["BodyText"], fontName="Helvetica", fontSize=8.7, leading=12, textColor=INK, leftIndent=13, firstLineIndent=-7, bulletIndent=4, spaceAfter=3.5),
        "caption": ParagraphStyle("Caption", parent=base["BodyText"], fontName="Helvetica", fontSize=7.5, leading=10, textColor=MUTED, alignment=TA_CENTER, spaceAfter=8),
        "table": ParagraphStyle("Table", parent=base["BodyText"], fontName="Helvetica", fontSize=7.3, leading=9.5, textColor=INK),
        "cover": ParagraphStyle("Cover", parent=base["Title"], fontName="Helvetica-Bold", fontSize=34, leading=40, textColor=INK, alignment=TA_CENTER),
        "cover_sub": ParagraphStyle("CoverSub", parent=base["BodyText"], fontName="Helvetica", fontSize=13, leading=18, textColor=GREEN, alignment=TA_CENTER),
    }


def page(canvas, doc) -> None:  # type: ignore[no-untyped-def]
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, width, height, stroke=0, fill=1)
    if doc.page > 1:
        canvas.setStrokeColor(LINE)
        canvas.line(20 * mm, height - 15 * mm, width - 20 * mm, height - 15 * mm)
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.setFillColor(GREEN)
        canvas.drawString(20 * mm, height - 11.5 * mm, "CONVERGE COMPOSED RELEASE")
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        footer = f"Converge {VERSION}  |  {doc.page}"
        canvas.drawRightString(width - 20 * mm, 11 * mm, footer)
    canvas.restoreState()


def table_flow(rows: list[str], style: dict[str, ParagraphStyle]) -> Table:
    parsed = []
    for index, row in enumerate(rows):
        cells = [item.strip() for item in row.strip().strip("|").split("|")]
        if index == 1 and all(re.fullmatch(r":?-{3,}:?", item) for item in cells):
            continue
        parsed.append([Paragraph(inline(cell), style["table"]) for cell in cells])
    columns = len(parsed[0])
    width = (A4[0] - 40 * mm) / columns
    result = Table(parsed, colWidths=[width] * columns, repeatRows=1, hAlign="LEFT")
    result.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GREEN),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return result


def document_story(path: pathlib.Path, style: dict[str, ParagraphStyle]) -> list[Flowable]:
    text = path.read_text(encoding="utf-8")
    if path == ROOT / "README.md":
        # The root licence link remains canonical online; repeating a one-word
        # terminal section in the guide creates a nearly empty release page.
        text = re.sub(r"\n## License\n.*\Z", "", text, flags=re.DOTALL)
    lines = text.splitlines()
    story: list[Flowable] = []
    paragraph: list[str] = []
    mermaid_index = 0

    def flush() -> None:
        if paragraph:
            story.append(Paragraph(inline(" ".join(part.strip() for part in paragraph)), style["body"]))
            paragraph.clear()

    index = 0
    while index < len(lines):
        line = lines[index]
        if line.strip() == "<!-- pagebreak -->":
            flush()
            story.append(PageBreak())
            index += 1
            continue
        if line.startswith("<div") or line.startswith("</div") or line.startswith("[!["):
            index += 1
            continue
        if line.startswith("```"):
            flush()
            language = line[3:].strip()
            body: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                body.append(lines[index])
                index += 1
            if language == "mermaid":
                mermaid_index += 1
                image_path = MERMAID_DIR / f"{path.stem.lower()}-{mermaid_index}.png"
                if not image_path.is_file():
                    raise FileNotFoundError(f"render Mermaid before PDF build: {image_path}")
                image = Image(str(image_path))
                max_width = A4[0] - 44 * mm
                # The architecture sequence diagram is tall enough to orphan
                # the final failure-posture sentence on a new page at 92 mm.
                # Tighten that one diagram while keeping every other visual at
                # the larger ceiling.
                max_height = (52 if path.name == "architecture.md" and mermaid_index == 2 else 92) * mm
                scale = min(max_width / image.imageWidth, max_height / image.imageHeight)
                image.drawWidth = image.imageWidth * scale
                image.drawHeight = image.imageHeight * scale
                image.hAlign = "CENTER"
                story.extend([Spacer(1, 4), image, Paragraph("Rendered from canonical Mermaid source.", style["caption"])])
            else:
                code = "\n".join(body)
                code_style = ParagraphStyle("Code", fontName="Courier", fontSize=6.8, leading=9, textColor=INK, backColor=colors.HexColor("#EEF3F0"), borderColor=LINE, borderWidth=0.5, borderPadding=7, spaceAfter=8)
                story.append(Preformatted(code, code_style, maxLineLength=104))
            index += 1
            continue
        if line.startswith("|"):
            flush()
            rows = []
            while index < len(lines) and lines[index].startswith("|"):
                rows.append(lines[index])
                index += 1
            story.extend([table_flow(rows, style), Spacer(1, 7)])
            continue
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            flush()
            level = len(heading.group(1))
            title = re.sub(r"<[^>]+>", "", heading.group(2))
            if level == 1:
                story.extend([PageBreak(), Paragraph(inline(title), style["h1"]), SectionRule()])
            else:
                story.append(Paragraph(inline(title), style[f"h{level}"]))
            index += 1
            continue
        bullet = re.match(r"^\s*-\s+(.+)$", line)
        if bullet:
            flush()
            story.append(Paragraph(inline(bullet.group(1)), style["bullet"], bulletText="-"))
            index += 1
            continue
        if not line.strip():
            flush()
        else:
            paragraph.append(line)
        index += 1
    flush()
    return story


def main() -> int:
    style = styles()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    width, height = A4
    doc = BaseDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=22 * mm,
        bottomMargin=18 * mm,
        title=f"Converge {VERSION} composed release guide",
        author="Converge project",
        subject="Canonical composed architecture and operating guide",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="release", frames=[frame], onPage=page)])
    story: list[Flowable] = [
        Spacer(1, 42 * mm),
        Paragraph("CONVERGE", style["cover"]),
        Spacer(1, 5 * mm),
        Paragraph(f"Composed release guide<br/>Version {VERSION}", style["cover_sub"]),
        Spacer(1, 10 * mm),
        Table(
            [[Paragraph("SEAMWISE", style["caption"]), Paragraph("TASK-SPEC", style["caption"]), Paragraph("CONVERGE", style["caption"])],
             [Paragraph("reviewed decomposition", style["body"]), Paragraph("task authority", style["body"]), Paragraph("coordination + settlement", style["body"])]],
            colWidths=[52 * mm] * 3,
            style=TableStyle([("BOX", (0, 0), (-1, -1), 0.8, GREEN), ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE), ("BACKGROUND", (0, 0), (-1, 0), MINT), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9)]),
        ),
        Spacer(1, 15 * mm),
        Paragraph("Release candidate: local evidence is documented; hosted CI and publication remain explicit gates.", style["cover_sub"]),
    ]
    for source in SOURCES:
        story.extend(document_story(source, style))
    doc.build(story)
    if not OUTPUT.is_file() or OUTPUT.stat().st_size < 10_000:
        raise SystemExit("PDF build is missing or implausibly small")
    print(f"PDF=READY path={OUTPUT} bytes={OUTPUT.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
