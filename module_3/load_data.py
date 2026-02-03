""" This module is to load cleaned GradCafe data into PostgreSQL

It reading module_2 output: llm_extend_applicant_data.json and loads into a single table called applicants.

- Uses p_id as the unique identifier (mapped from GradCafe result_id)
- Uses INSERT ... ON CONFLICT (p_id) DO UPDATE so we can safely re-run
"""

import argparse
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from db import get_cursor


TABLE_SQL = """
CREATE TABLE IF NOT EXISTS applicants (
    p_id INTEGER PRIMARY KEY,
    program TEXT,
    comments TEXT,
    date_added DATE,
    url TEXT,
    status TEXT,
    term TEXT,
    us_or_international TEXT,
    gpa DOUBLE PRECISION,
    gre DOUBLE PRECISION,
    gre_v DOUBLE PRECISION,
    gre_aw DOUBLE PRECISION,
    degree TEXT,
    llm_generated_program TEXT,
    llm_generated_university TEXT
);
"""

# Helpful indexes for queries in this assignment
INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_applicants_term ON applicants(term);",
    "CREATE INDEX IF NOT EXISTS idx_applicants_status ON applicants(status);",
    "CREATE INDEX IF NOT EXISTS idx_applicants_degree ON applicants(degree);",
    "CREATE INDEX IF NOT EXISTS idx_applicants_program ON applicants(program);",
    "CREATE INDEX IF NOT EXISTS idx_applicants_llm_prog ON applicants(llm_generated_program);",
    "CREATE INDEX IF NOT EXISTS idx_applicants_llm_univ ON applicants(llm_generated_university);",
]


def _parse_date(date_str: Optional[str]) -> Optional[str]:
    if not date_str:
        return None
    # Input looks like "January 27, 2026"
    for fmt in ("%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def normalize_row(r: Dict[str, Any]) -> Dict[str, Any]:
    """Map JSON keys to DB columns and normalize types."""
    pid_raw = r.get("result_id") or r.get("p_id")
    try:
        p_id = int(str(pid_raw).strip()) if pid_raw is not None else None
    except ValueError:
        p_id = None

    return {
        "p_id": p_id,
        "program": r.get("program"),
        "comments": r.get("comments"),
        "date_added": _parse_date(r.get("date_added")),
        "url": r.get("url"),
        "status": r.get("status"),
        "term": r.get("term"),
        "us_or_international": r.get("US/International") or r.get("us_or_international"),
        "gpa": _to_float(r.get("GPA") or r.get("gpa")),
        "gre": _to_float(r.get("GRE Score") or r.get("gre")),
        "gre_v": _to_float(r.get("GRE V Score") or r.get("gre_v")),
        "gre_aw": _to_float(r.get("GRE AW") or r.get("gre_aw")),
        "degree": r.get("Degree") or r.get("degree"),
        "llm_generated_program": r.get("llm-generated-program") or r.get("llm_generated_program"),
        "llm_generated_university": r.get("llm-generated-university") or r.get("llm_generated_university"),
    }


UPSERT_SQL = """
INSERT INTO applicants (
    p_id, program, comments, date_added, url, status, term, us_or_international,
    gpa, gre, gre_v, gre_aw, degree, llm_generated_program, llm_generated_university
) VALUES (
    %(p_id)s, %(program)s, %(comments)s, %(date_added)s, %(url)s, %(status)s, %(term)s, %(us_or_international)s,
    %(gpa)s, %(gre)s, %(gre_v)s, %(gre_aw)s, %(degree)s, %(llm_generated_program)s, %(llm_generated_university)s
)
ON CONFLICT (p_id) DO UPDATE SET
    program = EXCLUDED.program,
    comments = EXCLUDED.comments,
    date_added = EXCLUDED.date_added,
    url = EXCLUDED.url,
    status = EXCLUDED.status,
    term = EXCLUDED.term,
    us_or_international = EXCLUDED.us_or_international,
    gpa = EXCLUDED.gpa,
    gre = EXCLUDED.gre,
    gre_v = EXCLUDED.gre_v,
    gre_aw = EXCLUDED.gre_aw,
    degree = EXCLUDED.degree,
    llm_generated_program = EXCLUDED.llm_generated_program,
    llm_generated_university = EXCLUDED.llm_generated_university;
"""



def ensure_schema():
    with get_cursor() as cur:
        cur.execute(TABLE_SQL)
        for stmt in INDEX_SQL:
            cur.execute(stmt)


def load_json(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Expected a JSON list of rows.")
    return data


def load_rows(rows: List[Dict[str, Any]]) -> int:
    """Load rows into DB. Returns count inserted/updated (best-effort)."""
    ensure_schema()
    cleaned = []
    skipped = 0
    for r in rows:
        nr = normalize_row(r)
        if nr["p_id"] is None:
            skipped += 1
            continue
        cleaned.append(nr)

    with get_cursor() as cur:
        for r in cleaned:
            cur.execute(UPSERT_SQL, r)

    print(f"Loaded {len(cleaned)} rows. Skipped {skipped} rows missing/invalid result_id.")
    return len(cleaned)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json",
        default=os.path.join("..", "module_2", "llm_extend_applicant_data.json"),
        help="Path to cleaned JSON from module 2.",
    )
    args = parser.parse_args()

    rows = load_json(args.json)
    load_rows(rows)


if __name__ == "__main__":
    main()
