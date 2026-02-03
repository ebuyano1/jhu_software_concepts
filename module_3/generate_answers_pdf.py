"""
Creates answers_report.pdf which has :
- the requested assignment question
- the answer to the question
- SQL query that produced the answer
- short explanation of why the query answers the question

ToRun:
    python generate_answers_pdf.py
"""

from __future__ import annotations

import textwrap
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from query_data import get_analysis


def _wrap_lines(text: str, width: int = 95):
    lines = []
    for paragraph in str(text).splitlines():
        if not paragraph.strip():
            lines.append("")
            continue
        lines.extend(textwrap.wrap(paragraph, width=width))
    return lines


# Short “why” explanations keyed by question prefix (fallback if not found)
WHY = {
    "How many entries applied for Fall 2025?":
        "COUNT(*) with term ILIKE 'Fall 2025%' counts all records whose start term begins with 'Fall 2025'.",
    "What percentage of entries are international students (not American or Other)?":
        "We count rows where us_or_international is not American/Other, then divide by total rows to produce a percentage.",
    "What is the average GPA, GRE(Q), GRE V, GRE AW of applicants who provide these metrics?":
        "AVG() ignores NULLs. The WHERE clause ensures we only consider records where at least one metric is present.",
    "What is the average GPA of American students in Fall 2025?":
        "Filter by term 'Fall 2025%' and nationality 'American', then compute AVG(gpa) on the remaining rows.",
    "What percent of entries for Fall 2025 are Acceptances?":
        "Count Fall 2025 records and count those with status starting with 'Accepted', then compute the percentage.",
    "What is the average GPA of applicants who applied for Fall 2025 who are Acceptances?":
        "Filter Fall 2025 rows with Accepted status and compute AVG(gpa).",
    "How many entries are from applicants who applied to JHU for a masters degrees in Computer Science?":
        "Filter rows where program matches JHU and Computer Science and degree indicates a Masters, then COUNT(*).",
    "How many entries from 2025 are acceptances from applicants who applied to Georgetown University, MIT, Stanford University, or Carnegie Mellon University for a PhD in Computer Science?":
        "Filter by date range (year 2025), Accepted status, PhD degree, and matching university + CS program fields.",
    "Do the numbers change if you use LLM-generated fields (Q8 vs Q9)?":
        "We run the same filter logic using llm_generated_university and llm_generated_program to compare counts.",
}


def main(out_path: str = "answers_report.pdf") -> None:
    rows = get_analysis()

    c = canvas.Canvas(out_path, pagesize=letter)
    width, height = letter

    left = 0.75 * inch
    right = width - 0.75 * inch
    top = height - 0.75 * inch
    y = top

    c.setFont("Helvetica-Bold", 16)
    c.drawString(left, y, "Module 3 — Database Queries Report")
    y -= 0.25 * inch

    c.setFont("Helvetica", 10)
    c.drawString(left, y, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 0.35 * inch

    for i, item in enumerate(rows, start=1):
        q = item.get("question", "")
        a = item.get("answer", "")
        sql = item.get("sql", "")

        # Page break guard
        if y < 2.0 * inch:
            c.showPage()
            y = top

        c.setFont("Helvetica-Bold", 12)
        c.drawString(left, y, f"Q{i}. {q}")
        y -= 0.2 * inch

        c.setFont("Helvetica-Bold", 10)
        c.drawString(left, y, "Answer:")
        y -= 0.18 * inch

        c.setFont("Helvetica", 10)
        for line in _wrap_lines(a, width=95):
            if y < 1.2 * inch:
                c.showPage()
                y = top
                c.setFont("Helvetica", 10)
            c.drawString(left, y, line)
            y -= 0.14 * inch

        y -= 0.06 * inch
        c.setFont("Helvetica-Bold", 10)
        c.drawString(left, y, "SQL:")
        y -= 0.18 * inch

        c.setFont("Courier", 8.8)
        for line in _wrap_lines(sql, width=105):
            if y < 1.2 * inch:
                c.showPage()
                y = top
                c.setFont("Courier", 8.8)
            c.drawString(left, y, line)
            y -= 0.13 * inch

        y -= 0.06 * inch
        c.setFont("Helvetica-Bold", 10)
        c.drawString(left, y, "Why this query answers the question:")
        y -= 0.18 * inch

        c.setFont("Helvetica", 10)
        why = WHY.get(q, "This query filters the relevant records and uses SQL aggregates (COUNT/AVG) to compute the requested value.")
        for line in _wrap_lines(why, width=95):
            if y < 1.2 * inch:
                c.showPage()
                y = top
                c.setFont("Helvetica", 10)
            c.drawString(left, y, line)
            y -= 0.14 * inch

        y -= 0.25 * inch
        c.setStrokeColorRGB(0.85, 0.85, 0.85)
        c.line(left, y, right, y)
        y -= 0.25 * inch

    c.save()
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
