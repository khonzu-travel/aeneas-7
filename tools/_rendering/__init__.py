"""Vendored document-rendering engine (Markdown → print-ready PDF).

Copied from aeneas-6's `code/platform/src/aeneas/rendering/` package, minus
`renderer.py` (which renders *stored* artifact versions from the database —
not applicable here, since this repo has no platform). Only the parts
`tools/render_markdown_pdf.py` needs — Markdown parsing and PDF composition —
are vendored, so this tool has no dependency on a running platform or its
package layout.
"""
