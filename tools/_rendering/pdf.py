"""
Compose Markdown sections into one portable, print-ready PDF.

`build_document_pdf` is the one entry point: it takes a title, a cover, and a
list of `PdfSection`s and lays them out on the trim described below. Anything
that wants a document set for offline reading, review, or printing — an
operator tool, an export added later — calls it rather than growing a second
renderer beside this one.

The output is tuned for compact, high-contrast reading devices — e-ink panels
a document is annotated on — rather than for a desktop screen or a printer:

* **A small trim.** The page is a little narrower than A5 and about as tall, so
  a reader displaying it whole shows it at roughly 1:1 instead of scaling a
  letter-size page down to a third of the type size it was set at.
* **Type that survives that.** Body copy is set at `BODY_SIZE` (12pt) and never
  smaller; tabular and verbatim matter — tables, diagrams, code — is set at
  `DENSE_SIZE` (10pt) and never smaller. Nothing shrinks to fit: content that
  will not fit the measure changes *page orientation* instead.
* **Landscape where the content is wide.** A table whose columns cannot be set
  at 10pt within the portrait measure — because it has many columns, or long
  text in them, or both — is moved onto its own landscape page, as is a
  diagram whose lines are too long. The document returns to portrait after it.
* **Grayscale legibility.** Rules are black, the one fill is a light tint, and
  no meaning is carried by hue, so the page reads the same on a screen with no
  colour at all.

* **Glyphs the base-14 faces lack.** The defaults are Helvetica and Courier,
  which have no box-drawing characters; reportlab draws a filled rectangle
  rather than raising, so a diagram set in them fails silently. A caller that
  builds one document per process may call `use_unicode_fonts` first to adopt
  an installed face that covers it. See that function for why it is not on by
  default.

Usage:

    pdf_bytes = build_document_pdf(
        title="Field Notes",
        sections=[PdfSection(title="One", body=markdown), ...],
    )
"""

from __future__ import annotations

import io
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont, TTFontFile
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Flowable,
    Frame,
    HRFlowable,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)

from . import markdown_blocks as md

# --- page geometry ----------------------------------------------------------

#: Portrait trim. Sized to the visible area of a ~10in e-ink panel so the page
#: is shown at its native scale; landscape is the same sheet turned.
PAGE_WIDTH: Final[float] = 6.2 * inch
PAGE_HEIGHT: Final[float] = 8.27 * inch
PORTRAIT: Final[tuple[float, float]] = (PAGE_WIDTH, PAGE_HEIGHT)
LANDSCAPE: Final[tuple[float, float]] = (PAGE_HEIGHT, PAGE_WIDTH)

#: Narrow margins: on a small trim, every point of measure is type size the
#: reader does not have to give back.
MARGIN: Final[float] = 0.45 * inch
FOOTER_HEIGHT: Final[float] = 0.30 * inch

PORTRAIT_MEASURE: Final[float] = PAGE_WIDTH - 2 * MARGIN
LANDSCAPE_MEASURE: Final[float] = PAGE_HEIGHT - 2 * MARGIN

# --- type ------------------------------------------------------------------

#: Floor for running text. Nothing set as prose goes below this.
BODY_SIZE: Final[float] = 12.0
#: Floor for tabular and verbatim matter — tables, diagrams, code.
DENSE_SIZE: Final[float] = 10.0

#: Deliberately not Final: `use_unicode_fonts` rebinds these when a document
#: needs glyphs the base-14 faces lack. Everything built at call time reads
#: them, so the rebinding is how the swap reaches the whole module.
BODY_FONT: str = "Helvetica"
BOLD_FONT: str = "Helvetica-Bold"
ITALIC_FONT: str = "Helvetica-Oblique"
MONO_FONT: str = "Courier"

INK: Final[colors.Color] = colors.HexColor("#000000")
MUTED: Final[colors.Color] = colors.HexColor("#3C3C3C")
RULE: Final[colors.Color] = colors.HexColor("#4A4A4A")
TINT: Final[colors.Color] = colors.HexColor("#E4E4E4")
LINK: Final[str] = "#1A4F7A"

#: Heading sizes, largest first. The deepest headings sit at the body floor —
#: a heading is never smaller than the prose it introduces.
_HEADING_SIZES: Final[tuple[float, ...]] = (20.0, 16.5, 14.0, 13.0, 12.0, 12.0)

_CELL_PAD: Final[float] = 4.0
#: How wide one column is allowed to grow before its text wraps instead. Set
#: so that a handful of short columns still fits portrait, while a table of
#: several prose columns exceeds the measure and is turned.
_MAX_NATURAL_COL: Final[float] = 2.4 * inch
_MIN_COL: Final[float] = 0.5 * inch

#: Beyond this many columns the portrait measure gives each one under an inch:
#: the result is a grid the reader decodes rather than a table they read. Such
#: a table is turned even when its values are short enough to be squeezed in.
_PORTRAIT_COLUMN_LIMIT: Final[int] = 5


def _style(name: str, **kw: Any) -> ParagraphStyle:
    base: dict[str, Any] = {
        "fontName": BODY_FONT,
        "fontSize": BODY_SIZE,
        "leading": BODY_SIZE * 1.32,
        "textColor": INK,
        "spaceBefore": 0,
        "spaceAfter": 6,
    }
    base.update(kw)
    return ParagraphStyle(name, **base)


BODY_STYLE = _style("body", spaceAfter=7)
QUOTE_STYLE = _style(
    "quote",
    fontName=ITALIC_FONT,
    textColor=MUTED,
    leftIndent=12,
    borderPadding=0,
    spaceBefore=2,
    spaceAfter=8,
)
COVER_TITLE_STYLE = _style("coverTitle", fontName=BOLD_FONT, fontSize=26, leading=30, spaceAfter=10)
COVER_META_STYLE = _style("coverMeta", fontSize=BODY_SIZE, textColor=MUTED, spaceAfter=4)
CONTENTS_STYLE = _style("contents", spaceAfter=3, leftIndent=10, firstLineIndent=-10)
FENCED_STYLE = ParagraphStyle(
    "fenced",
    fontName=MONO_FONT,
    fontSize=DENSE_SIZE,
    leading=DENSE_SIZE * 1.25,
    textColor=INK,
    spaceBefore=2,
    spaceAfter=8,
)
CELL_STYLE = ParagraphStyle(
    "cell",
    fontName=BODY_FONT,
    fontSize=DENSE_SIZE,
    leading=DENSE_SIZE * 1.25,
    textColor=INK,
)
CELL_HEAD_STYLE = ParagraphStyle("cellHead", parent=CELL_STYLE, fontName=BOLD_FONT)
FOOTER_STYLE = _style("footer", fontSize=DENSE_SIZE, textColor=MUTED, spaceAfter=0)

#: Heading level → outline depth, for the reader's navigation pane.
_OUTLINE_LEVELS: Final[dict[str, int]] = {"h1": 0, "h2": 1, "h3": 2}


# --- glyph coverage ---------------------------------------------------------

#: The marks a document set by this module has to be able to carry.
#:
#: Derived from the characters this repository's Markdown actually uses, not
#: guessed at: the light box-drawing set diagrams are drawn with, the arrows a
#: transition is written with, and the typographic marks prose carries. A
#: caller that holds its own document should pass *that* instead — coverage is
#: then decided against what is really on the page. This constant exists for
#: the caller that has to choose a face before any document exists, which on a
#: server is every caller.
#:
#: Deliberately excludes U+25B6/U+25C0 and U+2208, which appear only rarely in
#: prose and would cost the metrically-compatible family for a handful of
#: occurrences.
REQUIRED_REPERTOIRE: Final[str] = (
    "─│┌┐└┘├┤┬┴┼"  # box drawing
    "←↑→↓↔"                                      # arrows
    "–—…§·²×▲▼"              # typographic
)

#: Candidate families, best first. Each maps this module's four font globals to
#: the files that replace them.
#:
#: The defaults above are base-14 Type 1 faces. ReportLab covers a missing
#: glyph by falling back to `Symbol` where it can — which is why arrows
#: (U+2190–21FF) come out correctly — and by drawing a **filled box** where it
#: cannot. Box-drawing characters (U+2500–257F) are the case that matters here:
#: this repository's design docs draw their diagrams with them, so a section
#: carrying one prints as a row of black rectangles, silently.
#:
#: Liberation leads because it is metrically compatible with Helvetica and
#: Courier — identical advance widths — so adopting it changes glyph coverage
#: and nothing else: every column width, and therefore every
#: portrait/landscape decision, is unchanged. DejaVu is wider, so a table that
#: only just fitted the portrait measure may turn.
_FONT_FAMILIES: Final[tuple[tuple[str, str, dict[str, tuple[str, str]]], ...]] = (
    (
        "Liberation",
        "/usr/share/fonts/truetype/liberation",
        {
            "BODY_FONT": ("LiberationSans", "LiberationSans-Regular.ttf"),
            "BOLD_FONT": ("LiberationSans-Bold", "LiberationSans-Bold.ttf"),
            "ITALIC_FONT": ("LiberationSans-Italic", "LiberationSans-Italic.ttf"),
            "MONO_FONT": ("LiberationMono", "LiberationMono-Regular.ttf"),
        },
    ),
    (
        "DejaVu",
        "/usr/share/fonts/truetype/dejavu",
        {
            "BODY_FONT": ("DejaVuSans", "DejaVuSans.ttf"),
            "BOLD_FONT": ("DejaVuSans-Bold", "DejaVuSans-Bold.ttf"),
            # Some packagings ship no Sans oblique; the upright stands in, so
            # emphasis loses its slant rather than the family being rejected
            # over the one face the document may not even use.
            "ITALIC_FONT": ("DejaVuSans-Italic", "DejaVuSans-Oblique.ttf"),
            "MONO_FONT": ("DejaVuSansMono", "DejaVuSansMono.ttf"),
        },
    ),
)


def _face_covers(path: str, codepoints: set[int]) -> bool:
    """True if the face at `path` has a glyph for every codepoint."""
    try:
        cmap = TTFontFile(path).charToGlyph
    except Exception:  # noqa: BLE001 — an unreadable face is simply not a candidate
        return False
    return codepoints.issubset(cmap.keys())


def use_unicode_fonts(text: str) -> str:
    """
    Point this module at installed faces that cover the glyphs `text` uses.

    Returns the family name adopted, or `""` when none qualifies — in which
    case the module is left exactly as it was and the caller decides whether a
    document with filled boxes in it is worth producing.

    Coverage is checked against the characters the document actually contains
    rather than assumed from a file being present, because the failure this
    guards against does not announce itself: reportlab substitutes rather than
    raises, so an unreadable diagram looks like a rendering that worked.

    **This is process-wide and one-way.** It rebinds the module's font globals
    and the styles built at import time, so every document built afterwards in
    this process uses the adopted family. Call it once, early, from a process
    that builds documents for one purpose — a CLI, a worker. A long-lived
    server that serves more than one caller should either call it at startup
    for all of them or not at all, never per request.
    """
    # Only characters outside the base-14 faces' own repertoire are at risk;
    # checking the ASCII range would just slow the cmap comparison down.
    needed = {ord(c) for c in set(text) if ord(c) > 0x7F}

    for family, directory, files in _FONT_FAMILIES:
        paths = {attr: f"{directory}/{name}" for attr, (_, name) in files.items()}

        # Body, bold and mono are what the document is actually set in, so all
        # three must be present. The italic is not: some packagings ship no
        # Sans oblique, and rejecting an otherwise-complete family over the one
        # face a document may contain none of is how a working fallback becomes
        # a dead one. Where it is absent the upright stands in, so emphasis
        # loses its slant and nothing else.
        required = ("BODY_FONT", "BOLD_FONT", "MONO_FONT")
        if not all(Path(paths[attr]).is_file() for attr in required):
            continue
        if not Path(paths["ITALIC_FONT"]).is_file():
            paths["ITALIC_FONT"] = paths["BODY_FONT"]
            files = {**files, "ITALIC_FONT": (files["BODY_FONT"][0], "")}

        # Body and mono carry the document between them, so both must cover it.
        if not (
            _face_covers(paths["BODY_FONT"], needed)
            and _face_covers(paths["MONO_FONT"], needed)
        ):
            continue

        old_to_new: dict[str, str] = {}
        for attr, (name, _) in files.items():
            # A stood-in italic resolves to a face already registered under the
            # body's name; registering it twice is harmless but pointless.
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, paths[attr]))
            old_to_new[globals()[attr]] = name
        normal, bold, italic = (
            files[k][0] for k in ("BODY_FONT", "BOLD_FONT", "ITALIC_FONT")
        )
        pdfmetrics.registerFontFamily(
            normal, normal=normal, bold=bold, italic=italic, boldItalic=bold
        )

        # Rebind the globals first: everything built at *call* time —
        # _style, _heading_style, the column measurements, the footer — reads
        # them.
        for attr, (name, _) in files.items():
            globals()[attr] = name

        # Then remap the styles built at *import* time, which captured the old
        # names as plain strings and cannot see the rebinding above.
        for value in list(globals().values()):
            if isinstance(value, ParagraphStyle):
                for field in ("fontName", "bulletFontName"):
                    if getattr(value, field, None) in old_to_new:
                        setattr(value, field, old_to_new[getattr(value, field)])
        return family
    return ""


def _heading_style(level: int) -> ParagraphStyle:
    size = _HEADING_SIZES[min(level, len(_HEADING_SIZES)) - 1]
    return _style(
        f"h{level}",
        fontName=BOLD_FONT,
        fontSize=size,
        leading=size * 1.25,
        spaceBefore=12 if level > 1 else 0,
        spaceAfter=5,
        keepWithNext=True,
    )


# --- column fitting ---------------------------------------------------------


def _measure_column(cells: list[str], font: str) -> float:
    """Width one column wants: its longest cell, capped so prose wraps."""
    widest = 0.0
    for cell in cells:
        for line in md.plain_text(cell).split("\n"):
            widest = max(widest, stringWidth(line, font, DENSE_SIZE))
    return min(widest + 2 * _CELL_PAD, _MAX_NATURAL_COL)


def natural_column_widths(table: md.Table) -> list[float]:
    """The width each column wants before any measure is imposed on it."""
    widths: list[float] = []
    for index in range(len(table.header)):
        header_width = stringWidth(
            md.plain_text(table.header[index]), BOLD_FONT, DENSE_SIZE
        ) + 2 * _CELL_PAD
        body_width = _measure_column([row[index] for row in table.rows], BODY_FONT)
        widths.append(max(min(header_width, _MAX_NATURAL_COL), body_width, _MIN_COL))
    return widths


def fit_column_widths(natural: list[float], measure: float) -> list[float]:
    """
    Fit columns to `measure` by capping the widest first.

    Wide columns give up space before narrow ones do, so a table of one prose
    column and four short ones keeps the short ones readable. Only if every
    column is already at the floor does the whole row scale down.
    """
    total = sum(natural)
    if total <= measure or not natural:
        return list(natural)

    low, high = 0.0, max(natural)
    for _ in range(60):
        cap = (low + high) / 2
        if sum(max(_MIN_COL, min(w, cap)) for w in natural) > measure:
            high = cap
        else:
            low = cap
    widths = [max(_MIN_COL, min(w, low)) for w in natural]

    total = sum(widths)
    if total > measure:
        widths = [w * measure / total for w in widths]
    return widths


def table_needs_landscape(table: md.Table) -> bool:
    """
    True when the table should be turned onto a landscape page.

    Either of the two ways a table outgrows the portrait measure is enough:
    it carries more columns than that measure can seat, or its content — long
    cells, or simply many of them — wants more width than the measure has.
    """
    if len(table.header) > _PORTRAIT_COLUMN_LIMIT:
        return True
    return sum(natural_column_widths(table)) > PORTRAIT_MEASURE


def _mono_columns(measure: float) -> int:
    """How many monospaced characters fit the measure at the dense floor."""
    return max(20, int(measure / stringWidth("0", MONO_FONT, DENSE_SIZE)))


def fenced_needs_landscape(block: md.Fenced) -> bool:
    """True when a verbatim block's longest line overruns the portrait measure."""
    return any(len(line.rstrip()) > _mono_columns(PORTRAIT_MEASURE) for line in block.lines)


def _wrapped_fenced_text(block: md.Fenced, measure: float) -> str:
    """
    Verbatim text for the measure, hard-wrapping only what still overruns it.

    Verbatim lines are not reflowed — a diagram loses its meaning if they are —
    so wrapping happens only for a line that would otherwise run off the page
    entirely, and only after the wider orientation has already been tried.
    """
    limit = _mono_columns(measure)
    out: list[str] = []
    for line in block.lines:
        text = line.rstrip()
        if not text:
            out.append("")
            continue
        while len(text) > limit:
            out.append(text[:limit])
            text = text[limit:]
        out.append(text)
    return "\n".join(out)


# --- flowables --------------------------------------------------------------


def _table_flowable(block: md.Table, measure: float) -> Flowable:
    widths = fit_column_widths(natural_column_widths(block), measure)
    data: list[list[Flowable]] = [
        [
            Paragraph(md.inline_markup(cell, code_font=MONO_FONT, link_color=LINK), CELL_HEAD_STYLE)
            for cell in block.header
        ]
    ]
    for row in block.rows:
        data.append(
            [
                Paragraph(md.inline_markup(cell, code_font=MONO_FONT, link_color=LINK), CELL_STYLE)
                for cell in row
            ]
        )

    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, RULE),
                ("BACKGROUND", (0, 0), (-1, 0), TINT),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), _CELL_PAD),
                ("RIGHTPADDING", (0, 0), (-1, -1), _CELL_PAD),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _list_flowables(block: md.ListBlock) -> list[Flowable]:
    out: list[Flowable] = []
    for item in block.items:
        indent = 12 + item.depth * 12
        style = _style(
            f"li{item.depth}",
            leftIndent=indent,
            bulletIndent=indent - 12,
            spaceAfter=3,
            # The marker is read as part of the sentence — an ordinal is prose,
            # not furniture — so it is set at the body size, not ReportLab's
            # smaller bullet default.
            bulletFontSize=BODY_SIZE,
            bulletFontName=BODY_FONT,
        )
        out.append(
            Paragraph(
                md.inline_markup(item.text, code_font=MONO_FONT, link_color=LINK),
                style,
                bulletText=item.marker,
            )
        )
    out.append(Spacer(1, 5))
    return out


def _block_flowables(block: md.Block) -> tuple[list[Flowable], bool]:
    """Render one block, and say whether it needs the page turned to landscape."""
    if isinstance(block, md.Heading):
        markup = md.inline_markup(block.text, code_font=MONO_FONT, link_color=LINK)
        return [Paragraph(markup, _heading_style(block.level))], False

    if isinstance(block, md.Paragraph):
        markup = md.inline_markup(block.text, code_font=MONO_FONT, link_color=LINK)
        return [Paragraph(markup, BODY_STYLE)], False

    if isinstance(block, md.ListBlock):
        return _list_flowables(block), False

    if isinstance(block, md.Quote):
        markup = md.inline_markup(block.text, code_font=MONO_FONT, link_color=LINK)
        return [Paragraph(markup, QUOTE_STYLE)], False

    if isinstance(block, md.Rule):
        rule = HRFlowable(width="100%", thickness=0.6, color=RULE, spaceAfter=8)
        return [Spacer(1, 4), rule], False

    if isinstance(block, md.Fenced):
        turned = fenced_needs_landscape(block)
        measure = LANDSCAPE_MEASURE if turned else PORTRAIT_MEASURE
        return [Preformatted(_wrapped_fenced_text(block, measure), FENCED_STYLE)], turned

    if isinstance(block, md.Table):
        if table_needs_landscape(block):
            return [_table_flowable(block, LANDSCAPE_MEASURE), Spacer(1, 9)], True
        # Keep a portrait table off the last inch of a page: a header row alone
        # at the foot of one page is worse than a little white space.
        return [
            CondPageBreak(1.2 * inch),
            _table_flowable(block, PORTRAIT_MEASURE),
            Spacer(1, 9),
        ], False

    return [], False  # pragma: no cover - the union above is exhaustive


def _blocks_to_flowables(blocks: list[md.Block]) -> list[Flowable]:
    """
    Lay a parsed document out, turning the page where the content demands it.

    A run of wide blocks shares one landscape stretch rather than taking a page
    each: the flow turns when it reaches content that needs the wider measure
    and turns back at the first block that does not, so consecutive wide tables
    do not leave an empty page between them. The document is left in whatever
    orientation its last block asked for — the section break that follows
    restores portrait, so returning here would only cost a blank page.
    """
    out: list[Flowable] = []
    turned = False

    for block in blocks:
        flowables, wants_landscape = _block_flowables(block)
        if not flowables:
            continue
        if wants_landscape != turned:
            out.append(NextPageTemplate("landscape" if wants_landscape else "portrait"))
            out.append(PageBreak())
            turned = wants_landscape
        out.extend(flowables)

    if turned:
        out.append(NextPageTemplate("portrait"))
    return out


# --- document ---------------------------------------------------------------


@dataclass(frozen=True)
class PdfSection:
    """One section of an exported document."""

    title: str
    body: str
    #: Optional line under the title — the group a collection document is in.
    label: str = ""


class _DocTemplate(BaseDocTemplate):  # type: ignore[misc]  # untyped base
    """
    Two page templates of one trim, plus a navigable outline.

    A reader with no page numbers to type still needs to get to the Security
    Model, so every heading down to the third level becomes an outline entry.
    """

    def __init__(
        self, buffer: io.BytesIO, *, title: str, author: str, running_head: str
    ) -> None:
        super().__init__(
            buffer,
            pagesize=PORTRAIT,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=MARGIN,
            bottomMargin=MARGIN + FOOTER_HEIGHT,
            title=title,
            author=author,
            subject=title,
            creator="AENEAS",
        )
        self._bookmarks = 0
        self._outline_depth = -1
        _draw_footer = _footer_drawer(running_head)
        self.addPageTemplates(
            [
                PageTemplate(
                    id="portrait",
                    pagesize=PORTRAIT,
                    frames=[
                        Frame(
                            MARGIN,
                            MARGIN + FOOTER_HEIGHT,
                            PORTRAIT_MEASURE,
                            PAGE_HEIGHT - 2 * MARGIN - FOOTER_HEIGHT,
                            id="portraitFrame",
                            leftPadding=0,
                            rightPadding=0,
                            topPadding=0,
                            bottomPadding=0,
                        )
                    ],
                    onPage=_draw_footer,
                ),
                PageTemplate(
                    id="landscape",
                    pagesize=LANDSCAPE,
                    frames=[
                        Frame(
                            MARGIN,
                            MARGIN + FOOTER_HEIGHT,
                            LANDSCAPE_MEASURE,
                            PAGE_WIDTH - 2 * MARGIN - FOOTER_HEIGHT,
                            id="landscapeFrame",
                            leftPadding=0,
                            rightPadding=0,
                            topPadding=0,
                            bottomPadding=0,
                        )
                    ],
                    onPage=_draw_footer,
                ),
            ]
        )

    def afterFlowable(self, flowable: Flowable) -> None:
        if not isinstance(flowable, Paragraph):
            return
        depth = _OUTLINE_LEVELS.get(flowable.style.name)
        if depth is None:
            return
        text = flowable.getPlainText().strip()
        if not text:
            return
        # An outline may not skip a level, and a document is free to open with
        # a third-level heading, so nest at most one step deeper than the entry
        # before it rather than refusing to build.
        depth = min(depth, self._outline_depth + 1)
        self._outline_depth = depth
        self._bookmarks += 1
        key = f"section-{self._bookmarks}"
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(text, key, level=depth, closed=(depth > 0))


def _footer_drawer(running_head: str) -> Callable[[Any, BaseDocTemplate], None]:
    """Page furniture: a hairline, the running head, and the folio."""

    def draw(canvas: Any, doc: BaseDocTemplate) -> None:
        width, _ = canvas._pagesize
        canvas.saveState()
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.4)
        y = MARGIN + FOOTER_HEIGHT - 4
        canvas.line(MARGIN, y, width - MARGIN, y)
        canvas.setFont(BODY_FONT, DENSE_SIZE)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, MARGIN - 1, running_head)
        canvas.drawRightString(width - MARGIN, MARGIN - 1, str(canvas.getPageNumber()))
        canvas.restoreState()

    return draw


def _cover(
    title: str,
    subtitle: str,
    cover_lines: Sequence[str],
    sections: list[PdfSection],
) -> list[Flowable]:
    """
    The opening page: title, an optional line under it, the caller's metadata,
    and the contents.

    `cover_lines` is inline markup, already escaped — a caller's metadata line
    may need an entity of its own (an em dash, say), so escaping here would
    print it literally.
    """
    out: list[Flowable] = [Paragraph(md.escape(title), COVER_TITLE_STYLE)]
    if subtitle:
        out.append(Paragraph(md.escape(subtitle), COVER_META_STYLE))
    out += [
        Spacer(1, 10),
        HRFlowable(width="100%", thickness=0.8, color=RULE, spaceAfter=12),
    ]
    out += [Paragraph(line, COVER_META_STYLE) for line in cover_lines]
    out.append(Spacer(1, 18))
    if sections:
        out.append(Paragraph("Contents", _heading_style(2)))
        for index, section in enumerate(sections, start=1):
            suffix = f" &mdash; {md.escape(section.label)}" if section.label else ""
            out.append(
                Paragraph(f"{index}.&nbsp;&nbsp;{md.escape(section.title)}{suffix}", CONTENTS_STYLE)
            )
    return out


def _without_repeated_title(blocks: list[md.Block], title: str) -> list[md.Block]:
    """
    Drop an opening heading that only repeats the section title.

    Authors commonly open a document with its own name. The export already
    sets that name as the section head, so printing it twice reads as an
    error rather than as structure.
    """
    if blocks and isinstance(blocks[0], md.Heading) and blocks[0].level <= 2:
        if md.plain_text(blocks[0].text).strip().casefold() == title.strip().casefold():
            return blocks[1:]
    return blocks


def build_document_pdf(
    *,
    title: str,
    sections: list[PdfSection],
    subtitle: str = "",
    running_head: str = "",
    cover_lines: Sequence[str] = (),
    empty_note: str = "This document has no content yet.",
    no_sections_note: str = "",
    generated_at: datetime | None = None,
    author: str = "AENEAS",
) -> bytes:
    """
    Compose Markdown sections into one portable document on this module's trim.

    `sections` arrive in reading order; each starts a fresh page so a section
    is never split across a boundary, and each becomes a contents entry and an
    outline bookmark. A document with no sections still produces a valid file —
    a cover carrying `no_sections_note` — rather than an error, because
    "nothing is written yet" is a true answer to the request.

    `cover_lines` is pre-escaped inline markup (see `_cover`). `running_head`
    defaults to the title.
    """
    generated_at = generated_at or datetime.now(UTC)
    buffer = io.BytesIO()
    doc = _DocTemplate(
        buffer, title=title, author=author, running_head=running_head or title
    )

    story: list[Flowable] = [NextPageTemplate("portrait")]
    story.extend(_cover(title, subtitle, cover_lines, sections))

    if not sections and no_sections_note:
        story.append(Spacer(1, 16))
        story.append(
            Paragraph(no_sections_note, _style("empty", fontName=ITALIC_FONT, textColor=MUTED))
        )

    for section in sections:
        story.append(PageBreak())
        heading: list[Flowable] = [Paragraph(md.escape(section.title), _heading_style(1))]
        if section.label:
            heading.append(Paragraph(md.escape(section.label), COVER_META_STYLE))
        heading.append(HRFlowable(width="100%", thickness=0.6, color=RULE, spaceAfter=10))
        story.append(KeepTogether(heading))
        body = section.body.strip()
        if body:
            blocks = _without_repeated_title(md.parse_blocks(body), section.title)
            story.extend(_blocks_to_flowables(blocks))
        elif empty_note:
            story.append(
                Paragraph(empty_note, _style("emptyDoc", fontName=ITALIC_FONT, textColor=MUTED))
            )

    doc.build(story)
    return buffer.getvalue()
