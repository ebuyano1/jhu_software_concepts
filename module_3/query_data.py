"""
This module is to query the applicants database to answer questions that are in requirements document

To Run:
python query_data.py

This prints answers to console and exposes a get_analysis() function used by Flask

Note:
All database querying code is in one place so the Flask app can stay clean
If something breaks with SQL execution,  only have to fix it here in one place
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union

from db import get_cursor

# psycopg2 supports:
#   - positional params (tuple/list) with %s placeholders
#   - named params (dict) with %(name)s placeholders
#
# IMPORTANT BUG FIXED:
# If a query has no parameters, we should call cur.execute(sql) with ONE argument.
# Passing an empty dict as the second argument can cause:
#   TypeError: dict is not a sequence
# depending on the SQL and psycopg2 expectations.
Params = Optional[Union[Dict[str, Any], Sequence[Any]]]


def _execute(cur, sql: str, params: Params = None) -> None:
    """
    Internal helper so we execute SQL correctly in one consistent place

    note:
    This wrapper exists because I hit a subtle psycopg2 behavior:
    cur.execute(sql, {}) is NOT the same as cur.execute(sql) and it can crash
    """
    if params is None:
        cur.execute(sql)
    else:
        cur.execute(sql, params)


def q_scalar(sql: str, params: Params = None) -> Any:
    """
    Run a query that returns a single scalar value (ex: COUNT(*), AVG(gpa), etc.).
    Returns the first column of the first row, or None if no rows.
    """
    with get_cursor() as cur:
        _execute(cur, sql, params)
        row = cur.fetchone()
        return row[0] if row else None


def q_row(sql: str, params: Params = None):
    """
    Run a query that returns a single row.
    Returns the row (tuple) or None if nothing returned.
    """
    with get_cursor() as cur:
        _execute(cur, sql, params)
        return cur.fetchone()


def q_all(sql: str, params: Params = None):
    """
    Run a query that returns multiple rows.
    Returns a list of rows (each row is a tuple).
    """
    with get_cursor() as cur:
        _execute(cur, sql, params)
        return cur.fetchall()


def pct(numer: float | int | None, denom: float | int | None) -> float | None:
    """
    Helper for percentage calculations.
    Returns None if the numerator is None or denominator is None/0 to avoid
    crashing and to make the output nicer in the UI.
    """
    if numer is None or denom in (None, 0):
        return None
    return round((float(numer) / float(denom)) * 100.0, 2)


def get_analysis() -> List[Dict[str, Any]]:
    """
    Return list of dictionaries containing:
      - question (string)
      - answer (value or nested structure)
      - sql (the query we used)

    note:
    I include the SQL in the output because the assignment page can show it and
    it also makes debugging much easier.
    """
    analysis: List[Dict[str, Any]] = []

    # 1) How many entries applied for Fall 2025?
    sql1 = "SELECT COUNT(*) FROM applicants WHERE term ILIKE 'Fall 2025%';"
    a1 = q_scalar(sql1)
    analysis.append({"question": "How many entries applied for Fall 2025?", "answer": a1, "sql": sql1})

    # 2) What percentage of entries are international students?
    # (Definition per assignment: not American and not Other)
    sql_total = "SELECT COUNT(*) FROM applicants;"
    total = q_scalar(sql_total)

    sql2 = """
        SELECT COUNT(*)
        FROM applicants
        WHERE us_or_international IS NOT NULL
          AND us_or_international NOT ILIKE 'American%'
          AND us_or_international NOT ILIKE 'Other%';
    """
    intl = q_scalar(sql2)
    a2 = pct(intl, total)
    analysis.append({
        "question": "What percentage of entries are international students (not American or Other)?",
        "answer": f"{a2:.2f}%" if a2 is not None else "N/A",
        "sql": sql2.strip()
    })

    # 3) Average GPA and GRE metrics for applicants who provide them
    # note:
    # We keep rows where ANY metric exists so we're not averaging over all-null records.
    sql3 = """
        SELECT
            AVG(gpa)   AS avg_gpa,
            AVG(gre)   AS avg_gre_q,
            AVG(gre_v) AS avg_gre_v,
            AVG(gre_aw) AS avg_gre_aw
        FROM applicants
        WHERE gpa IS NOT NULL
           OR gre IS NOT NULL
           OR gre_v IS NOT NULL
           OR gre_aw IS NOT NULL;
    """
    r3 = q_row(sql3)
    analysis.append({
        "question": "What is the average GPA, GRE(Q), GRE V, GRE AW of applicants who provide these metrics?",
        "answer": {
            "avg_gpa": round(r3[0], 2) if r3 and r3[0] is not None else None,
            "avg_gre_q": round(r3[1], 2) if r3 and r3[1] is not None else None,
            "avg_gre_v": round(r3[2], 2) if r3 and r3[2] is not None else None,
            "avg_gre_aw": round(r3[3], 2) if r3 and r3[3] is not None else None,
        },
        "sql": sql3.strip()
    })

    # 4) Average GPA of American students in Fall 2025
    sql4 = """
        SELECT AVG(gpa)
        FROM applicants
        WHERE term ILIKE 'Fall 2025%'
          AND us_or_international ILIKE 'American%'
          AND gpa IS NOT NULL;
    """
    a4 = q_scalar(sql4)
    analysis.append({
        "question": "What is the average GPA of American students in Fall 2025?",
        "answer": round(a4, 2) if a4 is not None else None,
        "sql": sql4.strip()
    })

    # 5) Percent of Fall 2025 entries that are acceptances
    sql5_total = "SELECT COUNT(*) FROM applicants WHERE term ILIKE 'Fall 2025%';"
    fall25_total = q_scalar(sql5_total)

    sql5_acc = "SELECT COUNT(*) FROM applicants WHERE term ILIKE 'Fall 2025%' AND status ILIKE 'Accepted%';"
    fall25_acc = q_scalar(sql5_acc)

    a5 = pct(fall25_acc, fall25_total)
    analysis.append({
        "question": "What percent of Fall 2025 entries are acceptances?",
        "answer": f"{a5:.2f}%" if a5 is not None else "N/A",
        "sql": sql5_acc
    })

    # 6) Average GPA of acceptances in Fall 2025
    sql6 = """
        SELECT AVG(gpa)
        FROM applicants
        WHERE term ILIKE 'Fall 2025%'
          AND status ILIKE 'Accepted%'
          AND gpa IS NOT NULL;
    """
    a6 = q_scalar(sql6)
    analysis.append({
        "question": "What is the average GPA of Fall 2025 acceptances?",
        "answer": round(a6, 2) if a6 is not None else None,
        "sql": sql6.strip()
    })

    # 7) JHU Masters in CS (based on raw program fields)
    sql7 = """
        SELECT COUNT(*)
        FROM applicants
        WHERE program ILIKE '%Johns Hopkins%'
          AND degree ILIKE 'Master%'
          AND program ILIKE '%Computer Science%';
    """
    a7 = q_scalar(sql7)
    analysis.append({
        "question": "How many entries applied to JHU for a Masters in Computer Science?",
        "answer": a7,
        "sql": sql7.strip()
    })

    # 8) 2025 acceptances for PhD CS at specific universities (raw fields)
    sql8 = """
        SELECT COUNT(*)
        FROM applicants
        WHERE date_added >= DATE '2025-01-01'
          AND date_added <  DATE '2026-01-01'
          AND status ILIKE 'Accepted%'
          AND degree ILIKE 'PhD%'
          AND program ILIKE '%Computer Science%'
          AND (
              program ILIKE '%Georgetown University%'
              OR program ILIKE '%MIT%'
              OR program ILIKE '%Massachusetts Institute of Technology%'
              OR program ILIKE '%Stanford University%'
              OR program ILIKE '%Carnegie Mellon University%'
          );
    """
    a8 = q_scalar(sql8)
    analysis.append({
        "question": "How many 2025 acceptances for PhD CS at Georgetown, MIT, Stanford, or CMU (raw fields)?",
        "answer": a8,
        "sql": sql8.strip()
    })

    # 9) Same question but using LLM-generated standardized fields
    sql9 = """
        SELECT COUNT(*)
        FROM applicants
        WHERE date_added >= DATE '2025-01-01'
          AND date_added <  DATE '2026-01-01'
          AND status ILIKE 'Accepted%'
          AND degree ILIKE 'PhD%'
          AND llm_generated_program ILIKE '%Computer Science%'
          AND llm_generated_university IN (
              'Georgetown University',
              'Massachusetts Institute of Technology',
              'MIT',
              'Stanford University',
              'Carnegie Mellon University'
          );
    """
    a9 = q_scalar(sql9)
    analysis.append({
        "question": "Do the numbers change if you use LLM-generated fields (Q8 vs Q9)?",
        "answer": {"raw_fields": a8, "llm_fields": a9},
        "sql": sql9.strip()
    })

    # 10) Two extra questions (these are meant to be editable / exploratory)

    # Extra Q1: Top 10 universities (LLM standardized) for Fall 2025
    sql10a = """
        SELECT llm_generated_university, COUNT(*) AS n
        FROM applicants
        WHERE term ILIKE 'Fall 2025%'
        GROUP BY llm_generated_university
        ORDER BY n DESC
        LIMIT 10;
    """
    top_unis = q_all(sql10a)
    analysis.append({
        "question": "Extra Q1: What are the top 10 universities (LLM standardized) people applied to for Fall 2025?",
        "answer": [{"university": r[0], "count": r[1]} for r in top_unis],
        "sql": sql10a.strip()
    })

    # Extra Q2: Status breakdown for Fall 2025
    sql10b = """
        SELECT status, COUNT(*) AS n
        FROM applicants
        WHERE term ILIKE 'Fall 2025%'
        GROUP BY status
        ORDER BY n DESC;
    """
    statuses = q_all(sql10b)
    analysis.append({
        "question": "Extra Q2: What is the breakdown of statuses for Fall 2025?",
        "answer": [{"status": r[0], "count": r[1]} for r in statuses],
        "sql": sql10b.strip()
    })

    return analysis


def main() -> None:
    """
    Console runner so we can quickly verify answers without Flask.
    note: This helped me debug SQL before wiring into the webpage.
    """
    rows = get_analysis()
    print("\n--- Module 3 Query Answers ---\n")
    for i, item in enumerate(rows, start=1):
        print(f"Q{i}: {item['question']}")
        print(f"Answer: {item['answer']}")
        print(f"SQL: {item['sql']}")
        print("-" * 60)


if __name__ == "__main__":
    main()
