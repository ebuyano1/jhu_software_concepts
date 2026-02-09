# This is used to query the data and has all of the SQL commands and explanation/logic loaded into List
#

from __future__ import annotations
from typing import Any, Dict, List, Optional, Sequence, Union
from db import get_cursor

def q_all(sql: str) -> List[Sequence[Any]]:
    with get_cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()

def format_percentage(value):
    """Helper to add % sign if value exists"""
    return f"{value}%" if value is not None else "0%"

def get_analysis() -> List[Dict[str, Any]]:
    analysis = []

    # --- Questions 1-9 (Required) ---

    # Q1
    q1_sql = "SELECT COUNT(*) FROM applicants WHERE term LIKE 'Fall 2025%';"
    rows = q_all(q1_sql)
    ans1 = rows[0][0] if rows else 0
    analysis.append({
        "id": "q1",
        "question": "How many total applications were submitted for the Fall 2025 term?",
        "answer": f"{ans1} applications",
        "sql": q1_sql,
        "explanation": "Counts all rows where the term starts with 'Fall 2025'."
    })

    # Q2
 # Q2 (UPDATED FOR SAFETY)
    q2_sql = """
        SELECT 
            CASE 
                WHEN (SELECT COUNT(*) FROM applicants) = 0 THEN 0
                ELSE ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM applicants), 2)
            END
        FROM applicants 
        WHERE us_or_international NOT IN ('American', 'Other');
    """
    rows = q_all(q2_sql)
    ans2 = format_percentage(rows[0][0]) if rows else "0%"
    analysis.append({
        "id": "q2",
        "question": "What percentage of all applicants are international (non-American)?",
        "answer": ans2,
        "sql": q2_sql,
        "explanation": "Calculates the ratio of applicants who are not 'American' or 'Other' against the total count."
    })

    # Q3
    q3_sql = "SELECT ROUND(AVG(gpa)::numeric, 2), ROUND(AVG(gre)::numeric, 2), ROUND(AVG(gre_v)::numeric, 2), ROUND(AVG(gre_aw)::numeric, 2) FROM applicants;"
    rows = q_all(q3_sql)
    if rows and rows[0][0]:
        gpa, gre, gre_v, gre_aw = rows[0]
        ans3 = f"GPA: {gpa} | GRE Quant: {gre} | GRE Verbal: {gre_v} | GRE AW: {gre_aw}"
    else:
        ans3 = "No data available"
    analysis.append({
        "id": "q3",
        "question": "What are the average GPA and GRE scores (Quant, Verbal, AW) across the entire dataset?",
        "answer": ans3,
        "sql": q3_sql,
        "explanation": "Computes the average for GPA and all GRE sections, rounding to 2 decimal places."
    })

    # Q4
    q4_sql = "SELECT ROUND(AVG(gpa)::numeric, 2) FROM applicants WHERE us_or_international = 'American' AND term LIKE 'Fall 2025%';"
    rows = q_all(q4_sql)
    ans4 = rows[0][0] if rows and rows[0][0] else "No data"
    analysis.append({
        "id": "q4",
        "question": "What is the average GPA of American students who applied for Fall 2025?",
        "answer": f"{ans4}",
        "sql": q4_sql,
        "explanation": "Filters for American students in Fall 2025 and averages their GPA."
    })

    # Q5
 
 # Q5 (UPDATED FOR SAFETY)
    q5_sql = """
        SELECT 
            CASE 
                WHEN (SELECT COUNT(*) FROM applicants WHERE term LIKE 'Fall 2025%') = 0 THEN 0
                ELSE ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM applicants WHERE term LIKE 'Fall 2025%'), 2)
            END
        FROM applicants 
        WHERE status = 'Accepted' AND term LIKE 'Fall 2025%';
    """
    rows = q_all(q5_sql)
    ans5 = format_percentage(rows[0][0]) if rows else "0%"
    analysis.append({
        "id": "q5",
        "question": "What is the overall acceptance rate for the Fall 2025 term?",
        "answer": ans5,
        "sql": q5_sql,
        "explanation": "Divides the number of 'Accepted' students by the total number of applicants for Fall 2025."
    })

    # Q6
    q6_sql = "SELECT ROUND(AVG(gpa)::numeric, 2) FROM applicants WHERE status = 'Accepted' AND term LIKE 'Fall 2025%';"
    rows = q_all(q6_sql)
    ans6 = rows[0][0] if rows and rows[0][0] else "No data"
    analysis.append({
        "id": "q6",
        "question": "What is the average GPA of students who were accepted for Fall 2025?",
        "answer": f"{ans6}",
        "sql": q6_sql,
        "explanation": "Averages the GPA only for students with 'Accepted' status in Fall 2025."
    })

    # Q7
    q7_sql = "SELECT COUNT(*) FROM applicants WHERE (university ILIKE '%JHU%' OR university ILIKE '%Johns Hopkins%') AND degree = 'Masters' AND program ILIKE '%Computer Science%';"
    rows = q_all(q7_sql)
    ans7 = rows[0][0] if rows else 0
    analysis.append({
        "id": "q7",
        "question": "How many applicants for a Masters in Computer Science applied to Johns Hopkins (JHU)?",
        "answer": f"{ans7} applicants",
        "sql": q7_sql,
        "explanation": "Filters for JHU (using wildcards) and Masters CS programs."
    })

    # Q8
    q8_sql = "SELECT COUNT(*) FROM applicants WHERE EXTRACT(YEAR FROM date_added) = 2025 AND status = 'Accepted' AND university IN ('Georgetown University', 'MIT', 'Stanford University', 'Carnegie Mellon University') AND degree = 'PhD' AND program ILIKE '%Computer Science%';"
    rows = q_all(q8_sql)
    ans8 = rows[0][0] if rows else 0
    analysis.append({
        "id": "q8",
        "question": "Using original fields: How many CS PhD applicants were accepted to Georgetown, MIT, Stanford, or CMU in 2025?",
        "answer": f"{ans8} applicants",
        "sql": q8_sql,
        "explanation": "JUSTIFICATION: We used the 'date_added' field because the question asks for acceptances 'in 2025' (the calendar year the result was received), rather than 'for the term of 2025'. This distinguishes immediate results from future term starts."
    })

    # Q9
    q9_sql = "SELECT COUNT(*) FROM applicants WHERE EXTRACT(YEAR FROM date_added) = 2025 AND status = 'Accepted' AND llm_generated_university IN ('Georgetown University', 'MIT', 'Stanford University', 'Carnegie Mellon University') AND degree = 'PhD' AND llm_generated_program ILIKE '%Computer Science%';"
    rows = q_all(q9_sql)
    ans9 = rows[0][0] if rows else 0
    analysis.append({
        "id": "q9",
        "question": "Using LLM fields: How many CS PhD applicants were accepted to Georgetown, MIT, Stanford, or CMU in 2025?",
        "answer": f"{ans9} applicants",
        "sql": q9_sql,
        "explanation": "JUSTIFICATION: Same logic as Q8 (using 'date_added' for calendar year). We use the LLM-cleaned university names here to capture variations like 'Carnegie Mellon' vs 'CMU'."
    })

    # --- Extra Questions (10 & 11) ---

    # Q10
    q10_sql = "SELECT llm_generated_program, COUNT(*) as count FROM applicants GROUP BY 1 ORDER BY 2 DESC LIMIT 1;"
    rows = q_all(q10_sql)
    if rows:
        prog, count = rows[0]
        ans10 = f"{prog} ({count} applications)"
    else:
        ans10 = "No data"
    analysis.append({
        "id": "q10",
        "question": "Extra Q1: Which academic program has the highest volume of application entries?",
        "answer": ans10,
        "sql": q10_sql,
        "explanation": "Groups by program name and sorts descending to find the most popular one."
    })

    # Q11
    q11_sql = "SELECT degree, ROUND(AVG(gre)::numeric, 2) as avg_q FROM applicants WHERE degree IN ('PhD', 'Masters') GROUP BY 1;"
    rows = q_all(q11_sql)
    
    # Format list into a readable string
    if rows:
        parts = []
        for r in rows:
            degree_name = r[0]
            score = r[1]
            parts.append(f"{degree_name}: {score}")
        ans11 = " | ".join(parts)
    else:
        ans11 = "No data"

    analysis.append({
        "id": "q11",
        "question": "Extra Q2: How does the average GRE Quantitative score compare between PhD and Masters applicants?",
        "answer": ans11,
        "sql": q11_sql,
        "explanation": "Groups by degree type to compare average GRE scores side-by-side."
    })

    return analysis

if __name__ == "__main__":
    results = get_analysis()
    for item in results:
        print(f"Q: {item['question']}")
        print(f"A: {item['answer']}\n")