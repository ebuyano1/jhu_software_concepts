"""
query_data.py — Module 5
Runs SQL analysis queries for the Flask /analysis page.
"""

from __future__ import annotations
from typing import Any, Dict, List
from psycopg import sql
from db import get_cursor

# Software Assurance Constant (Rule 6: Limit the number of rows evaluated)
MAX_ALLOWED_LIMIT = 100

def clamp_limit(requested: int) -> int:
    """Clamps the limit to the instructor-required range (1–100)."""
    return max(1, min(requested, MAX_ALLOWED_LIMIT))

def format_percentage(value: Any) -> str:
    """Helper to add a % sign if the value exists."""
    return f"{value}%" if value is not None else "0%"

def get_q1() -> Dict[str, Any]:
    """Query 1: Total applications for Fall 2025."""
    limit_val = clamp_limit(1)
    stmt = sql.SQL("SELECT COUNT(*) FROM {table} WHERE term ILIKE %s LIMIT {lim}").format(
        table=sql.Identifier("applicants"),
        lim=sql.Literal(limit_val)
    )
    with get_cursor() as cur:
        cur.execute(stmt, ("Fall 2025%",))
        rows = cur.fetchall()
        display_sql = stmt.as_string(cur)

    ans = rows[0][0] if rows else 0
    return {
        "id": "q1",
        "question": "How many total applications were submitted for the Fall 2025 term?",
        "answer": f"{ans} applications",
        "sql": display_sql,
        "explanation": "Counts all rows where the term starts with 'Fall 2025'.",
    }

def get_q2() -> Dict[str, Any]:
    """Query 2: Percentage of international applicants."""
    limit_val = clamp_limit(1)
    stmt = sql.SQL("""
        SELECT
            CASE
                WHEN (SELECT COUNT(*) FROM {table}) = 0 THEN 0
                ELSE ROUND(
                    100.0 * (
                        SELECT COUNT(*)
                        FROM {table}
                        WHERE us_or_international IS NOT NULL
                          AND us_or_international NOT ILIKE %s
                          AND us_or_international NOT ILIKE %s
                    ) / (SELECT COUNT(*) FROM {table}),
                2)
            END
        LIMIT {lim}
    """).format(
        table=sql.Identifier("applicants"),
        lim=sql.Literal(limit_val)
    )
    with get_cursor() as cur:
        cur.execute(stmt, ("American%", "Other%"))
        rows = cur.fetchall()
        display_sql = stmt.as_string(cur)

    ans = rows[0][0] if rows else 0
    return {
        "id": "q2",
        "question": "What percentage of all applicants are international (non-American)?",
        "answer": format_percentage(ans),
        "sql": display_sql,
        "explanation": "Calculates ratio of non-American/non-Other entries to the total.",
    }

def get_q3() -> Dict[str, Any]:
    """Query 3: Average GPA and GRE scores."""
    limit_val = clamp_limit(1)
    stmt = sql.SQL("""
        SELECT
            ROUND(AVG(gpa)::numeric, 2) AS avg_gpa,
            ROUND(AVG(gre)::numeric, 2) AS avg_gre_q,
            ROUND(AVG(gre_v)::numeric, 2) AS avg_gre_v,
            ROUND(AVG(gre_aw)::numeric, 2) AS avg_gre_aw
        FROM {table}
        WHERE gpa IS NOT NULL OR gre IS NOT NULL OR gre_v IS NOT NULL OR gre_aw IS NOT NULL
        LIMIT {lim}
    """).format(
        table=sql.Identifier("applicants"),
        lim=sql.Literal(limit_val)
    )
    with get_cursor() as cur:
        cur.execute(stmt)
        rows = cur.fetchall()
        display_sql = stmt.as_string(cur)

    avg_gpa, avg_q, avg_v, avg_aw = rows[0] if rows else (None, None, None, None)
    ans_lines = [
        f"Average GPA: {avg_gpa if avg_gpa is not None else 'N/A'}",
        f"Average GRE(Q): {avg_q if avg_q is not None else 'N/A'}",
        f"Average GRE(V): {avg_v if avg_v is not None else 'N/A'}",
        f"Average GRE(AW): {avg_aw if avg_aw is not None else 'N/A'}",
    ]
    return {
        "id": "q3",
        "question": "What are the average GPA and GRE scores across the entire dataset?",
        "answer": "\n".join(ans_lines),
        "sql": display_sql,
        "explanation": "Computes the mean for GPA and all three GRE components.",
    }

def get_q4() -> Dict[str, Any]:
    """Query 4: Average GPA of American Fall 2025 applicants."""
    limit_val = clamp_limit(1)
    stmt = sql.SQL("""
        SELECT ROUND(AVG(gpa)::numeric, 2)
        FROM {table}
        WHERE us_or_international ILIKE %s
          AND term ILIKE %s
          AND gpa IS NOT NULL
        LIMIT {lim}
    """).format(
        table=sql.Identifier("applicants"),
        lim=sql.Literal(limit_val)
    )
    with get_cursor() as cur:
        cur.execute(stmt, ("American%", "Fall 2025%"))
        rows = cur.fetchall()
        display_sql = stmt.as_string(cur)

    ans = rows[0][0] if rows else None
    return {
        "id": "q4",
        "question": "What is the average GPA of American students who applied for Fall 2025?",
        "answer": f"{ans}" if ans is not None else "N/A",
        "sql": display_sql,
        "explanation": "Filters by citizenship and term before averaging GPA.",
    }

def get_q5() -> Dict[str, Any]:
    """Query 5: Overall acceptance rate for Fall 2025."""
    limit_val = clamp_limit(1)
    stmt = sql.SQL("""
        WITH fall AS (SELECT COUNT(*) AS n_fall FROM {table} WHERE term ILIKE %s),
        acc AS (SELECT COUNT(*) AS n_acc FROM {table} WHERE term ILIKE %s AND status ILIKE %s)
        SELECT
            (SELECT n_acc FROM acc),
            (SELECT n_fall FROM fall),
            ROUND(100.0 * (SELECT n_acc FROM acc) / NULLIF((SELECT n_fall FROM fall), 0), 2)
        LIMIT {lim}
    """).format(
        table=sql.Identifier("applicants"),
        lim=sql.Literal(limit_val)
    )
    with get_cursor() as cur:
        cur.execute(stmt, ("Fall 2025%", "Fall 2025%", "Accepted%"))
        rows = cur.fetchall()
        display_sql = stmt.as_string(cur)

    acc_count, fall_count, percent = rows[0] if rows else (0, 0, 0)
    return {
        "id": "q5",
        "question": "What is the overall acceptance rate for the Fall 2025 term?",
        "answer": f"{format_percentage(percent)} ({acc_count} accepted out of {fall_count})",
        "sql": display_sql,
        "explanation": "Compares accepted counts against total Fall 2025 applications.",
    }

def get_q6() -> Dict[str, Any]:
    """Query 6: Average GPA of accepted Fall 2025 students."""
    limit_val = clamp_limit(1)
    stmt = sql.SQL("""
        SELECT ROUND(AVG(gpa)::numeric, 2)
        FROM {table}
        WHERE term ILIKE %s AND status ILIKE %s AND gpa IS NOT NULL
        LIMIT {lim}
    """).format(
        table=sql.Identifier("applicants"),
        lim=sql.Literal(limit_val)
    )
    with get_cursor() as cur:
        cur.execute(stmt, ("Fall 2025%", "Accepted%"))
        rows = cur.fetchall()
        display_sql = stmt.as_string(cur)

    ans = rows[0][0] if rows else None
    return {
        "id": "q6",
        "question": "What is the average GPA of students who were accepted for Fall 2025?",
        "answer": f"{ans}" if ans is not None else "N/A",
        "sql": display_sql,
        "explanation": "Averages GPA for the subset of students with an 'Accepted' status.",
    }

def get_q7() -> Dict[str, Any]:
    """Query 7: CS Masters applicants to JHU."""
    limit_val = clamp_limit(1)
    stmt = sql.SQL("""
        SELECT COUNT(*) FROM {table}
        WHERE (university ILIKE %s OR university ILIKE %s)
          AND degree ILIKE %s AND program ILIKE %s
        LIMIT {lim}
    """).format(
        table=sql.Identifier("applicants"),
        lim=sql.Literal(limit_val)
    )
    params = ("%Johns Hopkins%", "%JHU%", "Master%", "%Computer%Science%")
    with get_cursor() as cur:
        cur.execute(stmt, params)
        rows = cur.fetchall()
        display_sql = stmt.as_string(cur)

    ans = rows[0][0] if rows else 0
    return {
        "id": "q7",
        "question": "How many CS Masters applicants applied to Johns Hopkins (JHU)?",
        "answer": f"{ans} entries",
        "sql": display_sql,
        "explanation": "Filters by university name variations, degree level, and program.",
    }

def get_q8() -> Dict[str, Any]:
    """Query 8: CS PhD accepted to specific top schools."""
    limit_val = clamp_limit(1)
    stmt = sql.SQL("""
        SELECT COUNT(*) FROM {table}
        WHERE date_added >= %s::date AND date_added < %s::date
          AND status ILIKE %s AND degree ILIKE %s AND program ILIKE %s
          AND (university ILIKE %s OR university = %s OR university ILIKE %s
               OR university ILIKE %s OR university ILIKE %s)
        LIMIT {lim}
    """).format(
        table=sql.Identifier("applicants"),
        lim=sql.Literal(limit_val)
    )
    params = (
        "2025-01-01", "2026-01-01", "Accepted%", "PhD%", "%Computer%Science%",
        "%Georgetown University%", "MIT", "%Massachusetts Institute of Technology%",
        "%Stanford University%", "%Carnegie Mellon University%",
    )
    with get_cursor() as cur:
        cur.execute(stmt, params)
        rows = cur.fetchall()
        display_sql = stmt.as_string(cur)

    ans = rows[0][0] if rows else 0
    return {
        "id": "q8",
        "question": "How many CS PhD applicants were accepted to top schools in 2025?",
        "answer": f"{ans} entries",
        "sql": display_sql,
        "explanation": "Filters by top-tier universities, PhD degree, and 2025 date range.",
    }

def get_q9() -> Dict[str, Any]:
    """Query 9: Comparison of CS PhD acceptances."""
    limit_val = clamp_limit(1)
    stmt = sql.SQL("""
        WITH raw_c AS (
            SELECT COUNT(*) AS d_f FROM {table}
            WHERE date_added >= %s::date AND date_added < %s::date
              AND status ILIKE %s AND degree ILIKE %s AND program ILIKE %s
              AND (university ILIKE %s OR university = %s OR university ILIKE %s
                   OR university ILIKE %s OR university ILIKE %s)
        ),
        llm_c AS (
            SELECT COUNT(*) AS l_f FROM {table}
            WHERE date_added >= %s::date AND date_added < %s::date
              AND status ILIKE %s AND degree ILIKE %s AND llm_generated_program ILIKE %s
              AND (llm_generated_university ILIKE %s OR llm_generated_university = %s
                   OR llm_generated_university ILIKE %s OR llm_generated_university ILIKE %s
                   OR llm_generated_university ILIKE %s)
        )
        SELECT d_f, l_f, (l_f - d_f) FROM raw_c, llm_c
        LIMIT {lim}
    """).format(
        table=sql.Identifier("applicants"),
        lim=sql.Literal(limit_val)
    )
    p_params = (
        "2025-01-01", "2026-01-01", "Accepted%", "PhD%", "%Computer%Science%",
        "%Georgetown University%", "MIT", "%Massachusetts Institute of Technology%",
        "%Stanford University%", "%Carnegie Mellon University%"
    )
    with get_cursor() as cur:
        cur.execute(stmt, p_params + p_params)
        rows = cur.fetchall()
        display_sql = stmt.as_string(cur)

    raw_f, llm_f, diff = rows[0] if rows else (0, 0, 0)
    return {
        "id": "q9",
        "question": "How does acceptance compare between downloaded and LLM fields?",
        "answer": f"Raw: {raw_f}\nLLM: {llm_f}\nDifference: {diff}",
        "sql": display_sql,
        "explanation": "Compares data extracted from original fields vs. LLM-enriched fields.",
    }

def get_q10() -> Dict[str, Any]:
    """Query 10: Academic program volume."""
    limit_val = clamp_limit(1)
    stmt = sql.SQL("""
        SELECT COALESCE(llm_generated_program, program) AS prog, COUNT(*) AS c
        FROM {table} GROUP BY prog ORDER BY c DESC
        LIMIT {lim}
    """).format(
        table=sql.Identifier("applicants"),
        lim=sql.Literal(limit_val)
    )
    with get_cursor() as cur:
        cur.execute(stmt)
        rows = cur.fetchall()
        display_sql = stmt.as_string(cur)

    ans = f"{rows[0][0]} ({rows[0][1]} entries)" if rows else "N/A"
    return {
        "id": "q10",
        "question": "Which academic program has the highest volume of application entries?",
        "answer": ans,
        "sql": display_sql,
        "explanation": "Groups by program and returns the single most common program.",
    }

def get_q11() -> Dict[str, Any]:
    """Query 11: GRE Quant comparison PhD vs Masters."""
    limit_val = clamp_limit(5)
    stmt = sql.SQL("""
        SELECT
            CASE
                WHEN degree ILIKE %s THEN 'PhD'
                WHEN degree ILIKE %s THEN 'Masters'
                ELSE degree
            END,
            ROUND(AVG(gre)::numeric, 2)
        FROM {table} WHERE gre IS NOT NULL AND (degree ILIKE %s OR degree ILIKE %s)
        GROUP BY 1 ORDER BY 1
        LIMIT {lim}
    """).format(
        table=sql.Identifier("applicants"),
        lim=sql.Literal(limit_val)
    )
    params = ("PhD%", "Master%", "PhD%", "Master%")
    with get_cursor() as cur:
        cur.execute(stmt, params)
        rows = cur.fetchall()
        display_sql = stmt.as_string(cur)

    ans = "\n".join([f"{deg}: {score}" for deg, score in rows]) if rows else "N/A"
    return {
        "id": "q11",
        "question": "How does average GRE Quant compare between PhD and Masters applicants?",
        "answer": ans,
        "sql": display_sql,
        "explanation": "Groups GRE(Q) averages by degree type.",
    }

def get_analysis() -> List[Dict[str, Any]]:
    """Restores the function needed by app.py and pdf generator."""
    return [
        get_q1(), get_q2(), get_q3(), get_q4(), get_q5(),
        get_q6(), get_q7(), get_q8(), get_q9(), get_q10(), get_q11()
    ]
