"""Export markdown reports to PDF using fpdf2."""

from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos


def _sanitize(text: str) -> str:
    """Make text safe for Helvetica core font (latin-1)."""
    if not text:
        return ""
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "-",
        "\u2026": "...",
        "\u00a0": " ",
        "—": "-",
        "–": "-",
        "`": "'",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _strip_md_inline(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace("**", "").replace("*", "").replace("_", "")
    return _sanitize(text)


class ReportPDF(FPDF):
    def header(self) -> None:
        self.set_font("Helvetica", "B", 14)
        self.cell(
            0,
            10,
            "Job Search & Resume Report",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="C",
        )
        self.ln(4)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def _content_width(pdf: FPDF) -> float:
    return pdf.w - pdf.l_margin - pdf.r_margin


def _write_block(pdf: FPDF, text: str, line_height: float = 5, bold: bool = False, size: int = 11) -> None:
    """Write a paragraph with margin reset and explicit width (avoids fpdf2 w=0 bugs)."""
    text = _strip_md_inline(text)
    if not text:
        return

    pdf.set_x(pdf.l_margin)
    style = "B" if bold else ""
    pdf.set_font("Helvetica", style=style, size=size)
    width = _content_width(pdf)

    # fpdf2 can fail on a single over-long token; break very long words
    safe_parts: list[str] = []
    for word in text.split(" "):
        while len(word) > 80:
            safe_parts.append(word[:80])
            word = word[80:]
        if word:
            safe_parts.append(word)
    safe_text = " ".join(safe_parts)

    pdf.multi_cell(width, line_height, safe_text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def export_report_pdf(markdown_text: str, output_path: str | Path | None = None) -> bytes:
    """
    Convert markdown-ish report to PDF.
    Returns PDF bytes; optionally writes to output_path.
    """
    pdf = ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            pdf.ln(3)
            continue

        if line.startswith("# "):
            _write_block(pdf, line[2:].strip(), line_height=8, bold=True, size=16)
            pdf.ln(2)
        elif line.startswith("## "):
            _write_block(pdf, line[3:].strip(), line_height=7, bold=True, size=13)
            pdf.ln(1)
        elif line.startswith("### "):
            _write_block(pdf, line[4:].strip(), line_height=6, bold=True, size=12)
        elif line.startswith("#### "):
            _write_block(pdf, line[5:].strip(), line_height=6, bold=True, size=11)
        elif line.startswith(("- ", "* ")):
            _write_block(pdf, line[2:].strip(), line_height=5, size=11)
        elif line.startswith("**") and "**" in line[2:]:
            inner = line.strip("*").strip()
            _write_block(pdf, inner, line_height=5, bold=True, size=11)
        else:
            _write_block(pdf, line, line_height=5, size=11)

    out = pdf.output()
    pdf_bytes = out if isinstance(out, bytes) else bytes(out)

    if output_path:
        Path(output_path).write_bytes(pdf_bytes)

    return pdf_bytes


def export_report_pdf_to_buffer(markdown_text: str) -> BytesIO:
    buf = BytesIO(export_report_pdf(markdown_text))
    buf.seek(0)
    return buf
