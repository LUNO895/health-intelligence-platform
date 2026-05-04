"""Optional PDF export via fpdf2."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

try:
    from fpdf import FPDF
except ImportError:  # pragma: no cover
    FPDF = None  # type: ignore


def export_combined_pdf(report: Dict[str, Any], out_path: str | Path) -> Path:
    if FPDF is None:
        raise RuntimeError("Install fpdf2: pip install fpdf2")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 8, "Health Intelligence Report", ln=True)
    pdf.ln(2)
    pdf.set_font("Helvetica", size=10)

    compact = json.dumps(report, indent=2, ensure_ascii=False)
    for line in compact.splitlines():
        pdf.multi_cell(0, 5, line[:120])
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(path))
    return path
