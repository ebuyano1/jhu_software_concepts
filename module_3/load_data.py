"""load_data.py — Module 3 (schema with university + program)

This version matches the table schema YOU specified so Question 9 can compare:
- downloaded `university` vs `llm_generated_university`

Key decisions (assignment- and dataset-aligned):
- p_id is derived from the numeric id in the full GradCafe URL (…/result/<id>)
- the full URL is preserved in the `url` column
- works with the instructor dataset (overview_url, applicant_status, start_term, citizenship, etc.)
- supports --reset to drop + recreate the table deterministically
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from db import get_cursor


# -------------------------------------------------------------------
# Schema (EXACT per your latest spec)
# -------------------------------------------------------------------
DROP_TABLE_SQL = "DROP TABLE IF EXISTS applicants;"

CREATE_TABLE_SQL = """
CREATE TABLE applicants (
    p_id INTEGER PRIMARY KEY,
    university TEXT,               -- Downloaded Field
    program TEXT,                  -- Downloaded Field
    comments TEXT,
    date_added DATE,
    url TEXT,
    status TEXT,
    term TEXT,
    us_or_international TEXT,
    gpa FLOAT,
    gre FLOAT,
    gre_v FLOAT,
    gre_aw FLOAT,
    degree TEXT,
    llm_generated_program TEXT,    -- LLM Generated Field
    llm_generated_university TEXT  -- LLM Generated Field
);
"""


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
_RESULT_ID_RE = re.compile(r"/result/(\d+)")


def _extract_p_id(r: Dict[str, Any]) -> Optional[int]:
    """Extract numeric GradCafe result ID from overview_url/url."""
    url = r.get("overview_url") or r.get("url") or r.get("URL")
    if not url:
        return None
    m = _RESULT_ID_RE.search(str(url))
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
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


def _to_date(v: Any) -> Optional[datetime.date]:
    if not v:
        return None
    s = str(v).strip()
    for fmt in ("%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def normalize_row(r: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a JSON row to match the applicants table."""
    p_id = _extract_p_id(r)

    # Instructor dataset uses explicit university/program fields.
    university = r.get("university") or r.get("University")
    program = r.get("program") or r.get("Program")

    return {
        "p_id": p_id,
        "university": university,
        "program": program,
        "comments": r.get("comments") or r.get("Comments"),
        "date_added": _to_date(r.get("date_added") or r.get("Date Added")),
        "url": r.get("overview_url") or r.get("url") or r.get("URL"),
        "status": r.get("applicant_status") or r.get("status") or r.get("Status"),
        "term": r.get("start_term") or r.get("term") or r.get("Term"),
        "us_or_international": (
            r.get("citizenship")
            or r.get("US/International")
            or r.get("us_or_international")
        ),
        "gpa": _to_float(r.get("gpa") if "gpa" in r else r.get("GPA")),
        "gre": _to_float(r.get("gre_general") if "gre_general" in r else r.get("GRE Score")),
        "gre_v": _to_float(r.get("gre_verbal") if "gre_verbal" in r else r.get("GRE V Score")),
        "gre_aw": _to_float(r.get("gre_aw") if "gre_aw" in r else r.get("GRE AW")),
        "degree": r.get("degree_level") or r.get("Degree") or r.get("degree"),
        "llm_generated_program": r.get("llm-generated-program") or r.get("llm_generated_program"),
        "llm_generated_university": r.get("llm-generated-university") or r.get("llm_generated_university"),
    }


UPSERT_SQL = """
INSERT INTO applicants (
    p_id, university, program, comments, date_added, url, status, term,
    us_or_international, gpa, gre, gre_v, gre_aw, degree,
    llm_generated_program, llm_generated_university
) VALUES (
    %(p_id)s, %(university)s, %(program)s, %(comments)s, %(date_added)s, %(url)s, %(status)s, %(term)s,
    %(us_or_international)s, %(gpa)s, %(gre)s, %(gre_v)s, %(gre_aw)s, %(degree)s,
    %(llm_generated_program)s, %(llm_generated_university)s
)
ON CONFLICT (p_id) DO UPDATE SET
    university = EXCLUDED.university,
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


def ensure_schema(reset: bool) -> None:
    with get_cursor() as cur:
        if reset:
            cur.execute(DROP_TABLE_SQL)
        cur.execute(CREATE_TABLE_SQL)


def load_json(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Expected a JSON list.")
    return data


def load_rows(rows: List[Dict[str, Any]], reset: bool = False) -> int:
    ensure_schema(reset)

    cleaned: List[Dict[str, Any]] = []
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

    print(f"Loaded {len(cleaned)} rows. Skipped {skipped} rows.")
    return len(cleaned)


def load_json_to_db(json_path: str, reset: bool = False) -> int:
    rows = load_json(json_path)
    return load_rows(rows, reset=reset)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json",
        default=os.path.join("..", "module_2", "llm_extend_applicant_data_liv.json"),
        help="Path to JSON dataset",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate table before loading",
    )
    args = parser.parse_args()

    rows = load_json(args.json)
    load_rows(rows, reset=args.reset)


if __name__ == "__main__":
    main()
