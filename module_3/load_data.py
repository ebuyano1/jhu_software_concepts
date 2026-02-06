"""Load cleaned GradCafe data into PostgreSQL.

This loader is compatible with BOTH:
1) Module 2 JSON shape (your original output), and
2) The instructor-provided JSON file for this assignment (Liv's dataset).

Key mappings for instructor dataset (example record keys):
- overview_url           -> url
- applicant_status       -> status
- start_term             -> term
- citizenship            -> us_or_international
- gre_general            -> gre
- gre_verbal             -> gre_v
- gre_aw                 -> gre_aw
- degree_level           -> degree
- llm-generated-program  -> llm_generated_program
- llm-generated-university -> llm_generated_university

Primary key (p_id):
- Uses result_id when present (Module 2 shape)
- Otherwise parses the numeric id from the URL (e.g., /result/994246)
"""

import argparse
import json
import os
import re
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

URL_ID_RE = re.compile(r"/result/(\d+)", re.IGNORECASE)


def _parse_float(val: Any) -> Optional[float]:
    """Best-effort float parsing for values that may be '', None, '3.97', etc."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if s == "" or s.lower() in {"null", "none", "nan"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_date(val: Any) -> Optional[str]:
    """Parse dates like 'January 27, 2026' into ISO 'YYYY-MM-DD' (Postgres DATE accepts it)."""
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    # Common GradCafe format: 'January 27, 2026'
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def _extract_p_id(rec: Dict[str, Any]) -> int:
    """Return integer p_id from record_id/result_id OR parse from URL."""
    # Module 2 shape
    for key in ("result_id", "p_id", "id"):
        if key in rec and str(rec.get(key)).strip().isdigit():
            return int(str(rec.get(key)).strip())

    # Instructor dataset shape
    url = rec.get("overview_url") or rec.get("url") or ""
    m = URL_ID_RE.search(str(url))
    if m:
        return int(m.group(1))

    # Fallback: deterministic hash (keeps UPSERT stable across runs)
    # Note: Python hash is salted per-run, so we avoid it. Use a stable checksum.
    import zlib
    blob = json.dumps(rec, sort_keys=True).encode("utf-8")
    return int(zlib.adler32(blob))


def _get(rec: Dict[str, Any], *keys: str) -> Any:
    """Return first non-empty value among keys."""
    for k in keys:
        if k in rec:
            v = rec.get(k)
            if v is None:
                continue
            if isinstance(v, str) and v.strip() == "":
                continue
            return v
    return None


def normalize_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a raw JSON record into the DB schema used by Module 3."""
    p_id = _extract_p_id(rec)

    out = {
        "p_id": p_id,
        "program": _get(rec, "program", "Program", "llm-generated-program", "llm_generated_program"),
        "comments": _get(rec, "comments", "Comments"),
        "date_added": _parse_date(_get(rec, "date_added", "Date Added")),
        "url": _get(rec, "overview_url", "url", "URL"),
        "status": _get(rec, "applicant_status", "status", "Status"),
        "term": _get(rec, "start_term", "term", "Term"),
        "us_or_international": _get(rec, "citizenship", "US/International", "us_or_international"),
        "gpa": _parse_float(_get(rec, "gpa", "GPA")),
        "gre": _parse_float(_get(rec, "gre_general", "GRE Score", "GRE", "gre")),
        "gre_v": _parse_float(_get(rec, "gre_verbal", "GRE V Score", "GRE_V", "gre_v")),
        "gre_aw": _parse_float(_get(rec, "gre_aw", "GRE AW", "GRE_AW", "gre_aw")),
        "degree": _get(rec, "degree_level", "Degree", "degree"),
        "llm_generated_program": _get(rec, "llm-generated-program", "llm_generated_program"),
        "llm_generated_university": _get(rec, "llm-generated-university", "llm_generated_university"),
    }
    return out


def load_json_to_db(json_path: str, reset: bool = False) -> int:
    """Load JSON records into Postgres applicants table. Returns number of records processed."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Expected a JSON list of records.")

    rows = [normalize_record(r) for r in data if isinstance(r, dict)]

    with get_cursor() as cur:
        cur.execute(TABLE_SQL)

        if reset:
            # Delete existing data so the DB matches the instructor-provided dataset exactly.
            cur.execute("TRUNCATE TABLE applicants;")

        cur.executemany(UPSERT_SQL, rows)

    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Load GradCafe JSON data into PostgreSQL.")
    parser.add_argument(
        "--json",
        dest="json_path",
        default=None,
        help="Path to cleaned JSON file (instructor dataset or Module 2 output).",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="If set, TRUNCATE the applicants table before loading (delete old data).",
    )
    args = parser.parse_args()

    # Default search locations (supports either repo layout):
    # - module_2/llm_extend_applicant_data_liv.json (instructor file)
    # - module_2/llm_extend_applicant_data.json     (your Module 2 output)
    # - module_3/llm_extend_applicant_data_liv.json (if you keep the file in module_3)
    candidates = [
        os.path.join("..", "module_2", "llm_extend_applicant_data_liv.json"),
        os.path.join("..", "module_2", "llm_extend_applicant_data.json"),
        os.path.join(".", "llm_extend_applicant_data_liv.json"),
    ]

    json_path = args.json_path
    if not json_path:
        for c in candidates:
            if os.path.exists(c):
                json_path = c
                break

    if not json_path or not os.path.exists(json_path):
        raise FileNotFoundError(
            "Could not find a JSON file to load. Provide --json PATH, or place the instructor file at "
            "'module_2/llm_extend_applicant_data_liv.json'."
        )

    n = load_json_to_db(json_path, reset=args.reset)
    print(f"Loaded {n} records into PostgreSQL from: {json_path}")


if __name__ == "__main__":
    main()
