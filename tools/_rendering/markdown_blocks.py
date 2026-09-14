"""
A small Markdown block/inline reader for print rendering.

Artifact content is stored as Markdown (see `renderer.py`) and the web UI
hands it to `react-markdown`. A print renderer cannot reuse that: it needs the
document's *structure* — which blocks are tables, how many columns they carry,
how long their cells are — before it can decide how to lay a page out. So this
module parses the same GFM subset the UI renders into typed blocks, and
converts inline spans into ReportLab's inline markup.

The subset is deliberate: headings, paragraphs, fenced blocks, pipe tables,
bullet/ordered lists, block quotes and rules. Anything unrecognised falls
through as paragraph text rather than being dropped, so an authored document
never loses content to the parser.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Heading:
    level: int
    text: str


@dataclass(frozen=True)
class Paragraph:
    text: str


@dataclass(frozen=True)
class ListItem:
    text: str
    #: Nesting depth, 0 for a top-level item.
    depth: int
    #: The marker to print — a bullet, or the ordinal for an ordered list.
    marker: str


@dataclass(frozen=True)
class ListBlock:
    items: tuple[ListItem, ...]


@dataclass(frozen=True)
class Quote:
    text: str


@dataclass(frozen=True)
class Rule:
    pass


@dataclass(frozen=True)
class Fenced:
    """A fenced block: source, ASCII diagram, or anything else set verbatim."""

    lines: tuple[str, ...]
    language: str = ""


@dataclass(frozen=True)
class Table:
    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...] = field(default=())


Block = Heading | Paragraph | ListBlock | Quote | Rule | Fenced | Table


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE_RE = re.compile(r"^\s*(```+|~~~+)\s*([\w+-]*)\s*$")
_RULE_RE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")
_BULLET_RE = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_ORDERED_RE = re.compile(r"^(\s*)(\d{1,3})[.)]\s+(.*)$")
_QUOTE_RE = re.compile(r"^\s*>\s?(.*)$")
_TABLE_DIVIDER_RE = re.compile(r"^\s*\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)*\|?\s*$")


def _split_row(line: str) -> list[str]:
    """Split one pipe-table row, honouring `\\|` as a literal pipe."""
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|") and not stripped.endswith(r"\|"):
        stripped = stripped[:-1]
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for ch in stripped:
        if escaped:
            current.append(ch if ch == "|" else "\\" + ch)
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if escaped:
        current.append("\\")
    cells.append("".join(current).strip())
    return cells


def _is_table_start(lines: list[str], i: int) -> bool:
    return (
        "|" in lines[i]
        and i + 1 < len(lines)
        and "|" in lines[i + 1]
        and _TABLE_DIVIDER_RE.match(lines[i + 1]) is not None
    )


def parse_blocks(markdown: str) -> list[Block]:
    """Read Markdown source into the block sequence a page renderer lays out."""
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: list[Block] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        fence = _FENCE_RE.match(line)
        if fence:
            marker, language = fence.group(1), fence.group(2)
            body: list[str] = []
            i += 1
            while i < n:
                closing = _FENCE_RE.match(lines[i])
                if closing and closing.group(1)[0] == marker[0]:
                    i += 1
                    break
                body.append(lines[i])
                i += 1
            # Blank lines at either end are the fence's own padding, not part
            # of what was set inside it.
            while body and not body[0].strip():
                body.pop(0)
            while body and not body[-1].strip():
                body.pop()
            blocks.append(Fenced(lines=tuple(body), language=language))
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            blocks.append(Heading(level=len(heading.group(1)), text=heading.group(2)))
            i += 1
            continue

        if _RULE_RE.match(line):
            blocks.append(Rule())
            i += 1
            continue

        if _is_table_start(lines, i):
            header = tuple(_split_row(lines[i]))
            i += 2  # header + divider
            rows: list[tuple[str, ...]] = []
            while i < n and lines[i].strip() and "|" in lines[i]:
                cells = _split_row(lines[i])
                # Ragged rows are normalised to the header's width so the
                # table still renders rather than raising.
                if len(cells) < len(header):
                    cells = cells + [""] * (len(header) - len(cells))
                rows.append(tuple(cells[: len(header)]))
                i += 1
            blocks.append(Table(header=header, rows=tuple(rows)))
            continue

        if _BULLET_RE.match(line) or _ORDERED_RE.match(line):
            items: list[ListItem] = []
            while i < n:
                bullet = _BULLET_RE.match(lines[i])
                ordered = _ORDERED_RE.match(lines[i])
                if bullet:
                    depth = len(bullet.group(1).replace("\t", "  ")) // 2
                    items.append(
                        ListItem(text=bullet.group(2), depth=min(depth, 3), marker="•")
                    )
                elif ordered:
                    depth = len(ordered.group(1).replace("\t", "  ")) // 2
                    marker = f"{ordered.group(2)}."
                    items.append(
                        ListItem(text=ordered.group(3), depth=min(depth, 3), marker=marker)
                    )
                elif lines[i].strip() and lines[i].startswith((" ", "\t")) and items:
                    # A continuation line belongs to the item above it.
                    last = items[-1]
                    items[-1] = ListItem(
                        text=f"{last.text} {lines[i].strip()}", depth=last.depth, marker=last.marker
                    )
                else:
                    break
                i += 1
            blocks.append(ListBlock(items=tuple(items)))
            continue

        quote = _QUOTE_RE.match(line)
        if quote:
            body = [quote.group(1)]
            i += 1
            while i < n and (nxt := _QUOTE_RE.match(lines[i])) is not None:
                body.append(nxt.group(1))
                i += 1
            blocks.append(Quote(text=" ".join(part.strip() for part in body).strip()))
            continue

        # Paragraph: everything up to a blank line or the start of another block.
        para: list[str] = []
        while i < n and lines[i].strip():
            if (
                _HEADING_RE.match(lines[i])
                or _FENCE_RE.match(lines[i])
                or _RULE_RE.match(lines[i])
                or _QUOTE_RE.match(lines[i])
                or _is_table_start(lines, i)
                or (para and (_BULLET_RE.match(lines[i]) or _ORDERED_RE.match(lines[i])))
            ):
                break
            para.append(lines[i].strip())
            i += 1
        if para:
            blocks.append(Paragraph(text=" ".join(para)))
        else:  # pragma: no cover - defensive: never spin on an unconsumed line
            i += 1

    return blocks


# --- inline spans -----------------------------------------------------------

_CODE_SPAN_RE = re.compile(r"(`+)(.+?)\1", re.DOTALL)
_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_STRONG_RE = re.compile(r"(?<!\w)(\*\*|__)(?=\S)(.+?)(?<=\S)\1(?!\w)", re.DOTALL)
_EMPHASIS_RE = re.compile(r"(?<![\w*_])([*_])(?=[^\s*_])(.+?)(?<=[^\s*_])\1(?![\w*_])", re.DOTALL)
_STRIKE_RE = re.compile(r"~~(?=\S)(.+?)(?<=\S)~~", re.DOTALL)
_PLACEHOLDER = "\x00%d\x00"


def escape(text: str) -> str:
    """Escape the three characters ReportLab's inline parser treats as markup."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline_markup(text: str, *, code_font: str = "Courier", link_color: str = "#1A4F7A") -> str:
    """
    Convert inline Markdown into the mini-markup ReportLab paragraphs accept.

    Code spans are lifted out before anything else runs, so `**` inside a
    literal stays literal, and are put back once the surrounding emphasis has
    been resolved.
    """
    spans: list[str] = []

    def stash(match: re.Match[str]) -> str:
        spans.append(match.group(2).strip())
        return _PLACEHOLDER % (len(spans) - 1)

    stashed = _CODE_SPAN_RE.sub(stash, text)
    out = escape(stashed)
    out = _LINK_RE.sub(
        lambda m: f'<link href="{m.group(2)}" color="{link_color}">'
        f"{m.group(1) or m.group(2)}</link>",
        out,
    )
    out = _STRONG_RE.sub(lambda m: f"<b>{m.group(2)}</b>", out)
    out = _EMPHASIS_RE.sub(lambda m: f"<i>{m.group(2)}</i>", out)
    out = _STRIKE_RE.sub(lambda m: f"<strike>{m.group(1)}</strike>", out)

    for index, span in enumerate(spans):
        out = out.replace(
            _PLACEHOLDER % index, f'<font face="{code_font}">{escape(span)}</font>'
        )
    return out


def plain_text(text: str) -> str:
    """Strip inline markers — used for measuring, outlines and cover copy."""
    out = _CODE_SPAN_RE.sub(lambda m: m.group(2).strip(), text)
    out = _LINK_RE.sub(lambda m: m.group(1) or m.group(2), out)
    out = _STRONG_RE.sub(lambda m: m.group(2), out)
    out = _EMPHASIS_RE.sub(lambda m: m.group(2), out)
    out = _STRIKE_RE.sub(lambda m: m.group(1), out)
    return out
