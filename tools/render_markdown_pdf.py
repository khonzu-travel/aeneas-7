#!/usr/bin/env python
"""
Render this repository's Markdown design docs to a print-ready PDF.

`_rendering/pdf.py` sets a document for a ~10in e-ink panel: a small trim
shown at roughly 1:1 rather than scaled down, a 12pt body floor with nothing
allowed to shrink to fit, wide tables and diagrams turned to landscape instead
of squeezed, and grayscale throughout. `build_document_pdf` is that engine's
entry point. The engine is vendored under `tools/_rendering/` (copied from
aeneas-6's `code/platform/src/aeneas/rendering/`, minus the parts that render
artifact versions out of a running platform's database — this repo has
neither) so this tool has no dependency beyond `reportlab`.

This script is the command line over it, and deliberately holds nothing else:
splitting Markdown into sections is its own job, and everything below that
belongs to the vendored module.

Usage — one file:

    python tools/render_markdown_pdf.py design/overview.md out.pdf \
        --title "Document title" --subtitle "One line under it"

    Sections split on top-level (`##`) headings; each starts a fresh page and
    becomes a contents entry and an outline bookmark. Anything before the
    first `##` becomes the opening section, named by `--front`.

Usage — a whole directory (e.g. this repo's `design/`):

    python tools/render_markdown_pdf.py design/ design-01.pdf

    Every `.md` file under the directory becomes one chapter — one contents
    entry, starting a fresh page — titled by its own `#` heading. A chapter's
    internal `##`/`###` structure renders and outlines as usual; it is not
    split further, so the table of contents stays one entry per document
    instead of one per heading across three dozen files. Chapters are ordered
    by `DESIGN_MANIFEST` below, which mirrors the reading order this repo's
    own `README.md` and `design/README.md` describe; a file that exists on
    disk but is not yet named there is still included, appended in sorted
    order, with a warning — an unlisted file is a gap in the manifest, not a
    reason to drop it from the export.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _rendering import markdown_blocks as md  # noqa: E402
from _rendering.pdf import PdfSection, build_document_pdf, use_unicode_fonts  # noqa: E402

# --- single-file splitting ---------------------------------------------------

_H2 = re.compile(r"^##[ \t]+(.+?)[ \t]*$", re.MULTILINE)
#: A rule on its own line. Each section already starts a page, so a rule that
#: only separated sections in the source would print as a stray hairline under
#: a heading.
_EDGE_RULE = re.compile(r"\A(?:\s*-{3,}\s*\n)+|(?:\n\s*-{3,}\s*)+\Z")


def split_sections(markdown: str, front_title: str) -> tuple[str, list[PdfSection]]:
    """
    Split on top-level headings, returning (document title, sections).

    The document title is the leading `# ` heading if there is one; it is
    consumed rather than printed, because the cover sets it.
    """
    text = markdown.replace("\r\n", "\n").strip("\n")
    title = ""
    if text.startswith("# "):
        head, _, rest = text.partition("\n")
        title = md.plain_text(head[2:]).strip()
        text = rest.lstrip("\n")

    matches = list(_H2.finditer(text))
    sections: list[PdfSection] = []

    front = (text[: matches[0].start()] if matches else text).strip()
    front = _EDGE_RULE.sub("", front).strip()
    if front:
        sections.append(PdfSection(title=front_title, body=front))

    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end() : end].strip()
        body = _EDGE_RULE.sub("", body).strip()
        sections.append(PdfSection(title=md.plain_text(match.group(1)).strip(), body=body))

    return title, sections


# --- directory (whole design/ tree) ------------------------------------------

#: The reading order `README.md` and `design/README.md` describe, as paths
#: relative to the directory being rendered (normally `design/`). Kept as an
#: explicit list rather than derived from a scan, because the order is a
#: deliberate editorial choice — overview before decisions, decisions before
#: rules, rules before formats, formats before phases — not an alphabetical
#: accident. `discover_design_files` appends anything this list omits.
DESIGN_MANIFEST: list[str] = [
    "README.md",
    "overview.md",
    "changes-from-v6.md",
    "roles.md",
    "governance.md",
    "ledger/overview.md",
    "ledger/constitution.md",
    "ledger/feature-spec.md",
    "ledger/plan.md",
    "ledger/tasks.md",
    "ledger/data-model.md",
    "ledger/clarification.md",
    "ledger/amendment.md",
    "pipeline/overview.md",
    "pipeline/phase-1-specify.md",
    "pipeline/phase-2-plan.md",
    "pipeline/phase-3-schedule.md",
    "pipeline/phase-4-build.md",
    "pipeline/phase-5-integrate-release.md",
    "pipeline/phase-6-operate.md",
    "platform/overview.md",
    "platform/turn-queue.md",
    "platform/event-store.md",
    "platform/projections.md",
    "platform/concurrency.md",
    "platform/verification.md",
    "platform/database-schema.md",
    "platform/recovery.md",
    "workflows/main-workflow.md",
    "workflows/clarification.md",
    "workflows/review-and-rework.md",
    "workflows/blocked.md",
    "workflows/abandonment.md",
    "workflows/amendment.md",
    "workflows/data-model-change.md",
    "skills/README.md",
    "skills/plan/SKILL.md",
    "skills/review-data/SKILL.md",
]


def discover_design_files(root: Path) -> list[Path]:
    """Every `.md` file under `root`, in `DESIGN_MANIFEST` order, then extras."""
    manifest_paths = [root / rel for rel in DESIGN_MANIFEST]
    missing = [p for p in manifest_paths if not p.exists()]
    if missing:
        print(
            "warning: DESIGN_MANIFEST names file(s) not found, skipped: "
            + ", ".join(str(p.relative_to(root)) for p in missing),
            file=sys.stderr,
        )
    ordered = [p for p in manifest_paths if p.exists()]
    known = {p.resolve() for p in ordered}
    extra = sorted(p for p in root.rglob("*.md") if p.resolve() not in known)
    if extra:
        print(
            "warning: file(s) on disk but not in DESIGN_MANIFEST, appended in "
            "sorted order — add them to the manifest to fix their place: "
            + ", ".join(str(p.relative_to(root)) for p in extra),
            file=sys.stderr,
        )
    return ordered + extra


def file_to_section(path: Path, root: Path) -> PdfSection:
    """
    One design document as one chapter.

    Its own `# ` heading becomes the chapter title (consumed, not printed
    twice — `build_document_pdf` already drops a section's opening heading
    when it repeats the section title). Everything under it, `##`/`###`
    structure included, becomes the chapter body: unlike `split_sections`,
    this does not split further on `##`, so a whole file is one contents
    entry and one outline bookmark, with its internal headings nested one
    level deeper rather than flattened alongside every other file's.
    """
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").strip("\n")
    title = path.stem
    if text.startswith("# "):
        head, _, rest = text.partition("\n")
        title = md.plain_text(head[2:]).strip()
        text = rest.lstrip("\n")
    text = _EDGE_RULE.sub("", text).strip()
    return PdfSection(title=title, body=text, label=str(path.relative_to(root)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", type=Path, help="Markdown file, or a directory of them, to render")
    parser.add_argument("output", type=Path, help="PDF file to write")
    parser.add_argument(
        "--title",
        default="",
        help="cover title (default: the file's H1; 'AENEAS 7 — Design Specification' for a directory)",
    )
    parser.add_argument("--subtitle", default="", help="one line under the cover title")
    parser.add_argument(
        "--front", default="Overview", help="name for the pre-heading section (single-file mode only)"
    )
    parser.add_argument("--author", default="AENEAS", help="PDF author metadata")
    args = parser.parse_args(argv)

    if args.input.is_dir():
        files = discover_design_files(args.input)
        if not files:
            print(f"error: no Markdown files found under {args.input}", file=sys.stderr)
            return 1
        sections = [file_to_section(f, args.input) for f in files]
        combined_source = "\n\n".join(s.body for s in sections)
        title = args.title or "AENEAS 7 — Design Specification"
    else:
        combined_source = args.input.read_text(encoding="utf-8")
        parsed_title, sections = split_sections(combined_source, args.front)
        title = args.title or parsed_title
        if not sections:
            print(f"error: {args.input} has no content", file=sys.stderr)
            return 1

    # Safe here in a way it would not be inside a server: this process builds
    # exactly one document and exits.
    family = use_unicode_fonts(combined_source)
    if not family:
        print(
            "warning: no installed family covers this document; falling back to "
            "the base-14 faces, which have no glyph for box-drawing characters "
            "and will print them as filled boxes.",
            file=sys.stderr,
        )

    data = build_document_pdf(
        title=title,
        subtitle=args.subtitle,
        sections=sections,
        cover_lines=[f"Generated {datetime.now(UTC).strftime('%Y-%m-%d')}"],
        author=args.author,
    )
    args.output.write_bytes(data)
    print(
        f"{args.output} — {len(data) / 1024:.0f} KB, {len(sections)} section(s), "
        f"set in {family or 'base-14'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
