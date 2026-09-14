# Tools

Operator scripts. This repository is design-only otherwise (see the root
`CLAUDE.md`) — these are self-contained utilities that render its Markdown,
not part of the design.

## `render_markdown_pdf.py`

Renders one Markdown file, or a whole directory of them, to a print-ready
PDF — a small trim tuned for a ~10in e-reader, 12pt body floor, wide tables
and diagrams turned to landscape instead of shrunk, grayscale throughout.
The engine lives in `_rendering/` (vendored from aeneas-6's
`code/platform/src/aeneas/rendering/`, with the parts that read a running
platform's database left out); this tool's only external dependency is
`reportlab`.

```sh
pip install "reportlab>=4.2"

# One file
python tools/render_markdown_pdf.py design/overview.md overview.pdf

# The whole design/ tree — one chapter per file, in reading order
python tools/render_markdown_pdf.py design/ design-01.pdf
```

Directory mode orders chapters by `DESIGN_MANIFEST` in the script, which
mirrors the reading order `README.md` and `design/README.md` describe. A
file present on disk but missing from the manifest is still included
(appended, sorted, with a warning on stderr) rather than silently dropped —
update the manifest when you add a design document, so it lands where it
belongs in the reading order rather than at the end.

See the script's own docstring and `--help` for the rest of the options
(title, subtitle, author metadata).
