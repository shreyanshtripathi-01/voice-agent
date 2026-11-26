#!/usr/bin/env python3
"""Dev-only: render REPORT.md into a one-page PDF using only the standard library.

The app itself has no dependencies; this helper just produces a printable artifact.
Run: python3 tools/make_pdf.py
"""

from __future__ import annotations

import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "REPORT.md"
OUT = ROOT / "REPORT.pdf"

WIDTH, HEIGHT, MARGIN = 595, 842, 40  # A4 in points


def sanitize(text: str) -> str:
    replacements = {
        "₹": "Rs. ", "→": "->", "·": "-", "—": "-", "–": "-", "×": "x",
        "≈": "~", "≥": ">=", "≤": "<=", "“": '"', "”": '"', "‘": "'",
        "’": "'", "…": "...", "•": "-",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace("**", "").replace("`", "")
    return "".join(ch if 32 <= ord(ch) < 127 else " " for ch in text)


def parse(source: str):
    items = []
    for raw in source.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("# "):
            items.append(("h1", line[2:]))
        elif line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue
            items.append(("table", " | ".join(cells)))
        else:
            items.append(("body", line))
    return items


def layout(items, size: float):
    max_chars = int((WIDTH - 2 * MARGIN) / (size * 0.50))
    rows = []
    for kind, text in items:
        clean = sanitize(text)
        if kind == "h1":
            rows.append(("B", size + 3.5, clean))
            continue
        width = max_chars - 8 if kind == "table" else max_chars
        for segment in textwrap.wrap(clean, width=width) or [""]:
            rows.append(("B" if kind == "h1" else "R", size, segment))
    return rows


def build_pdf(rows) -> bytes:
    content = []
    y = HEIGHT - MARGIN
    for font, size, text in rows:
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        tag = "F2" if font == "B" else "F1"
        content.append(f"BT /{tag} {size} Tf 1 0 0 1 {MARGIN} {y:.1f} Tm ({escaped}) Tj ET")
        y -= size * 1.34
    stream = "\n".join(content).encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {WIDTH} {HEIGHT}] "
         f"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>").encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream",
    ]

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets[1:]:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def main() -> None:
    items = parse(SRC.read_text(encoding="utf-8"))
    for size in (9.5, 9.0, 8.5, 8.0, 7.5):
        rows = layout(items, size)
        if len(rows) <= 62:  # fits one A4 page
            break
    OUT.write_bytes(build_pdf(rows))
    print(f"Wrote {OUT.relative_to(ROOT)} — {len(rows)} lines at {size}pt")


if __name__ == "__main__":
    main()
