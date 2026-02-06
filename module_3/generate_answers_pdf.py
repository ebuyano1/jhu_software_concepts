"""
generate_answers_pdf.py
-----------------------
Creates a PDF report that includes each required question, its computed answer,
the SQL used, and a short explanation.

This version focuses on readability:
- If an answer is a dict (e.g., multiple averages), it prints each value on its
  own line with human-friendly labels (e.g., "Average GPA: 3.80").
- If an answer is a list, it prints items one per line.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Tuple

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from query_data import get_analysis


# Friendly label overrides for common structured outputs
LABEL_MAP = {
    "avg_gpa": "Average GPA",
    "avg_gre_q": "Average GRE (Q)",
    "avg_gre_v": "Average GRE (V)",
    "avg_gre_aw": "Average GRE (AW)",
    "avg_gre": "Average GRE",
    "avg_gre_general": "Average GRE (General)",
    "count": "Count",
    "num_applications": "Number of applications",
    "num_applicants": "Number of applicants",
    "num_accepted": "Number accepted",
    "percent_international": "Percent international",
    "acceptance_rate": "Acceptance rate",
    "pct": "Percent",
    "percentage": "Percent",
}


def _to_title_label(key: str) -> str:
    """Convert a snake_case key into a readable label if not in LABEL_MAP."""
    k = str(key).strip()
    if not k:
        return "Value"
    if k in LABEL_MAP:
        return LABEL_MAP[k]
    # Example: "us_or_international" -> "Us Or International" (fine fallback)
    return " ".join([w.capitalize() for w in k.replace("-", "_").split("_")])


def _format_number(key: str, value: Any) -> str:
    """
    Format numeric values nicely.
    - Use 2 decimals for floats (common for averages).
    - If key looks like a percent/rate, format as percentage when plausible.
    """
    if value is None:
        return "N/A"

    # Basic numeric coercion
    num = None
    if isinstance(value, (int, float)):
        num = float(value)
    else:
        try:
            num = float(str(value).strip())
        except Exception:
            return str(value)

    # Percent-ish keys
    k = str(key).lower()
    if any(token in k for token in ("percent", "pct", "rate")):
        # If it looks like 0.27, display 27.00%
        if 0 <= num <= 1:
            return f"{num * 100:.2f}%"
        return f"{num:.2f}%"

    # Common averages / scores: two decimals
    if abs(num) < 10000:
        # Keep ints clean
        if float(num).is_integer():
            return str(int(num))
        return f"{num:.2f}"

    return str(value)


def _answer_lines(answer: Any) -> List[str]:
    """
    Convert an answer (scalar, dict, list) into printable lines.
    """
    if answer is None:
        return ["N/A"]

    # Dict -> one line per key/value with friendly labels
    if isinstance(answer, dict):
        lines = []
        for k, v in answer.items():
            label = _to_title_label(k)
            val = _format_number(k, v)
            lines.append(f"{label}: {val}")
        return lines

    # List/Tuple -> one line per item
    if isinstance(answer, (list, tuple)):
        if len(answer) == 0:
            return ["(no rows)"]
        # If list items are dict-like, stringify each item compactly
        lines = []
        for item in answer:
            if isinstance(item, dict):
                # Try a compact "Key: Value" joined format per dict row
                parts = []
                for k, v in item.items():
                    parts.append(f"{_to_title_label(k)}={_format_number(k, v)}")
                lines.append(", ".join(parts))
            else:
                lines.append(str(item))
        return lines

    # Scalar
    return [str(answer)]


def _wrap_draw(c: canvas.Canvas, lines: List[str], x: float, y: float, max_width: float, line_height: float) -> float:
    """Draw lines with word wrapping; returns new y position."""
    for raw in lines:
        text = str(raw) if raw is not None else ""
        # Manual wrap
        words = text.split()
        if not words:
            y -= line_height
            continue
        line = ""
        for w in words:
            trial = (line + " " + w).strip()
            if c.stringWidth(trial) <= max_width:
                line = trial
            else:
                c.drawString(x, y, line)
                y -= line_height
                line = w
        if line:
            c.drawString(x, y, line)
            y -= line_height
    return y


def generate_pdf(output_path: str = "answers_report.pdf") -> str:
    analysis: List[Dict[str, Any]] = get_analysis()

    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter

    left = 0.75 * inch
    right = 0.75 * inch
    top = 0.75 * inch
    bottom = 0.75 * inch
    max_width = width - left - right

    y = height - top

    c.setFont("Helvetica-Bold", 14)
    c.drawString(left, y, "Module 3 — Answers Report")
    y -= 18

    c.setFont("Helvetica", 10)
    c.drawString(left, y, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 22

    for i, item in enumerate(analysis, start=1):
        if y < bottom + 140:
            c.showPage()
            y = height - top

        question = str(item.get("question", "")).strip()
        answer = item.get("answer", None)
        sql = str(item.get("sql", "")).strip()
        explanation = str(item.get("explanation", "")).strip()

        c.setFont("Helvetica-Bold", 12)
        c.drawString(left, y, f"Q{i}. {question}")
        y -= 16

        # Answer
        c.setFont("Helvetica-Bold", 10)
        c.drawString(left, y, "Answer:")
        y -= 14

        c.setFont("Helvetica", 10)
        ans_lines = _answer_lines(answer)
        y = _wrap_draw(c, ans_lines, left + 50, y, max_width - 50, 12)

        # SQL
        c.setFont("Helvetica-Bold", 10)
        c.drawString(left, y, "SQL:")
        y -= 14

        c.setFont("Courier", 9)
        y = _wrap_draw(c, [sql], left + 50, y, max_width - 50, 11)

        # Explanation
        if explanation:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(left, y, "Why this answers the question:")
            y -= 14
            c.setFont("Helvetica", 10)
            y = _wrap_draw(c, [explanation], left + 50, y, max_width - 50, 12)

        y -= 12

    c.save()
    return output_path


if __name__ == "__main__":
    path = generate_pdf()
    print(f"Wrote {path}")
