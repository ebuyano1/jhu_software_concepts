"""
load_data.py — Module 3 (FINAL, schema-correct, URL-preserving)

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
# Schema (EXACT per assignment)
# -------------------------------------------------------------------
DROP_TABLE_SQL = "DROP TABLE IF EXISTS applicants;"

CREATE_TABLE_SQL = """
CREATE TABLE applicants (
    p_id INTEGER PRIMARY KEY,
    university TEXT,
    program TEXT,
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
    llm_generated_program TEXT,
    llm_generated_university TEXT
);
"""

# We explicitly insert p_id because we extract it from the URL
UPSERT_SQL = """
INSERT INTO applicants (
    p_id, university, program, comments, date_added, url, status, term,
    us_or_international, gpa, gre, gre_v, gre_aw, degree,
    llm_generated_program, llm_generated_university
) VALUES (
    %(p_id)s, %(university)s, %(program)s, %(comments)s, %(date_added)s, %(url)s,
    %(status)s, %(term)s, %(us_or_international)s, %(gpa)s, %(gre)s,
    %(gre_v)s, %(gre_aw)s, %(degree)s,
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


# -------------------------------------------------------------------
# Logic
# -------------------------------------------------------------------

def normalize_row(r: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converts a raw JSON dict into a schema-compliant dict.
    - Extracts p_id from 'overview_url'
    - Parses 'date_added' to a Python date object
    - Converts numeric fields (gpa, gre, etc.) to float or None
    """
    # 1. Extract ID from URL (e.g. ".../result/12345")
    url = r.get("overview_url", "")
    p_id = None
    if url:
        # Regex to find the last numeric segment
        match = re.search(r'/result/(\d+)', url)
        if match:
            p_id = int(match.group(1))

    # 2. Parse Date (e.g. "20 Feb 2025" or similar)
    # The JSON usually has dates like "15 Feb 2026". We try standard formats.
    # Note: If JSON has "February 01, 2026", adjust the format string.
    raw_date = r.get("date_added")
    formatted_date = None
    if raw_date:
        # Attempt common GradCafe formats
        for fmt in ("%d %b %Y", "%B %d, %Y"):
            try:
                formatted_date = datetime.strptime(raw_date, fmt).date()
                break
            except ValueError:
                pass

    # 3. Helper for floats
    def to_float(val: Any) -> Optional[float]:
        if val is None or str(val).strip() == "":
            return None
        try:
            return float(val)
        except ValueError:
            return None

    return {
        "p_id": p_id,
        "university": r.get("university"),
        "program": r.get("program"),
        "comments": r.get("comments"),
        "date_added": formatted_date,
        "url": url,
        "status": r.get("applicant_status"),
        "term": r.get("start_term"),
        "us_or_international": r.get("citizenship"),
        "gpa": to_float(r.get("gpa")),
        "gre": to_float(r.get("gre_general")),
        "gre_v": to_float(r.get("gre_verbal")),
        "gre_aw": to_float(r.get("gre_aw")),
        "degree": r.get("degree_level"),
        "llm_generated_program": r.get("llm-generated-program"),
        "llm_generated_university": r.get("llm-generated-university"),
    }


def ensure_schema(reset: bool = False) -> None:
    """
    Creates the database schema.
    If reset is True, it drops the existing table first.
    """
    with get_cursor() as cur:
        if reset:
            cur.execute(DROP_TABLE_SQL)
            print("Existing 'applicants' table dropped.")
        
        # Use IF NOT EXISTS so we don't crash if it's already there (unless reset=True)
        try:
            cur.execute(CREATE_TABLE_SQL)
            print("Table 'applicants' created.")
        except Exception as e:
            # If table already exists and we didn't reset, ignore "duplicate table" error
            if "already exists" in str(e):
                print("Table 'applicants' already exists. Skipping create.")
            else:
                raise e


def load_json(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"JSON file not found at: {path}")
        
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

    print(f"Loaded {len(cleaned)} rows. Skipped {skipped} rows (missing ID).")
    return len(cleaned)


def load_json_to_db(json_path: str, reset: bool = False) -> int:
    rows = load_json(json_path)
    return load_rows(rows, reset=reset)


# REPLACE THE BOTTOM OF load_data.py WITH THIS:

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json",
        default="llm_extend_applicant_data_liv.json",
        help="Path to the JSON data file."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="If set, drops the table before loading."
    )
    args = parser.parse_args()

    # We removed the try/except block here so tests can see the crash directly
    load_json_to_db(args.json, reset=args.reset)

if __name__ == "__main__":
    main()