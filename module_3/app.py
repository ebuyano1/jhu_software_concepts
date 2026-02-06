"""
Flask app for Module 3 — Databases & Analysis Dashboard.

This version adds a small, readable presentation layer for the webpage:
- Some answers naturally come back as structured data (dict/list). Instead of showing
  raw Python objects, we format them into labeled lines like:
    "Average GPA: 3.80"
    "Average GRE (Q): 279.68"

Core assignment behavior is unchanged:
- Pull Data runs in the background and loads JSON into PostgreSQL.
- Update Analysis does nothing while Pull Data is running.
"""

from __future__ import annotations

import os
import threading
from typing import Any, Dict, List

from flask import Flask, jsonify, redirect, render_template, request, url_for

from load_data import load_json_to_db
from query_data import get_analysis

app = Flask(__name__)

# -------------------------------------------------------------------
# Shared state for the background "Pull Data" job
# -------------------------------------------------------------------
_pull_lock = threading.Lock()
_is_pulling: bool = False
_last_log: str = ""

# Friendly label overrides for common structured outputs
_LABEL_MAP = {
    "avg_gpa": "Average GPA",
    "avg_gre_q": "Average GRE (Q)",
    "avg_gre_v": "Average GRE (V)",
    "avg_gre_aw": "Average GRE (AW)",
    "avg_gre": "Average GRE",
    "count": "Count",
    "num_applications": "Number of applications",
    "num_applicants": "Number of applicants",
    "num_accepted": "Number accepted",
    "percent_international": "Percent international",
    "acceptance_rate": "Acceptance rate",
    "pct": "Percent",
    "percentage": "Percent",
}


def _to_label(key: str) -> str:
    k = str(key).strip()
    if not k:
        return "Value"
    if k in _LABEL_MAP:
        return _LABEL_MAP[k]
    # Fallback: snake_case -> Title Case
    return " ".join(w.capitalize() for w in k.replace("-", "_").split("_"))


def _format_number(key: str, value: Any) -> str:
    if value is None:
        return "N/A"

    # Numeric coercion
    num = None
    if isinstance(value, (int, float)):
        num = float(value)
    else:
        try:
            num = float(str(value).strip())
        except Exception:
            return str(value)

    k = str(key).lower()
    if any(tok in k for tok in ("percent", "pct", "rate")):
        # Treat 0..1 as a ratio, print as percent
        if 0 <= num <= 1:
            return f"{num * 100:.2f}%"
        return f"{num:.2f}%"

    if float(num).is_integer():
        return str(int(num))
    return f"{num:.2f}"


def format_answer_lines(answer: Any) -> List[str]:
    """
    Convert an answer into readable lines for the webpage.
    The goal is clarity, not showing raw Python objects.
    """
    if answer is None:
        return ["N/A"]

    if isinstance(answer, dict):
        lines: List[str] = []
        for k, v in answer.items():
            lines.append(f"{_to_label(k)}: {_format_number(k, v)}")
        return lines

    if isinstance(answer, (list, tuple)):
        if len(answer) == 0:
            return ["(no rows)"]
        lines = []
        for item in answer:
            if isinstance(item, dict):
                # Compact row formatting: Label=value, Label=value
                parts = []
                for k, v in item.items():
                    parts.append(f"{_to_label(k)}={_format_number(k, v)}")
                lines.append(", ".join(parts))
            else:
                lines.append(str(item))
        return lines

    # Scalar
    return [str(answer)]


@app.template_filter("pretty_answer")
def pretty_answer_filter(answer: Any) -> List[str]:
    """Jinja filter wrapper so templates can call: {{ item.answer | pretty_answer }}"""
    return format_answer_lines(answer)


def _default_json_candidates() -> list[str]:
    return [
        os.path.join("..", "module_2", "llm_extend_applicant_data_liv.json"),
        os.path.join("..", "module_2", "llm_extend_applicant_data.json"),
        os.path.join(".", "llm_extend_applicant_data_liv.json"),
        os.path.join(".", "llm_extend_applicant_data.json"),
    ]


def _resolve_json_path() -> str:
    env_path = os.environ.get("INSTRUCTOR_JSON_PATH", "").strip()
    if env_path and os.path.exists(env_path):
        return env_path

    for candidate in _default_json_candidates():
        if os.path.exists(candidate):
            return candidate

    return os.path.join("..", "module_2", "llm_extend_applicant_data_liv.json")


def _pull_state() -> Dict[str, object]:
    return {"is_pulling": _is_pulling, "last_log": _last_log}


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------
@app.get("/")
def root():
    return redirect(url_for("analysis_page"))


@app.get("/analysis")
def analysis_page():
    rows = get_analysis()
    return render_template("analysis.html", rows=rows, pull_state=_pull_state())


@app.get("/pull-status")
def pull_status():
    return jsonify({"ok": True, **_pull_state()})


@app.post("/update-analysis")
def update_analysis():
    if _is_pulling:
        return jsonify(
            {"ok": False, "error": "Pull Data is currently running, so Update Analysis is disabled right now."}
        ), 409

    _ = get_analysis()
    return jsonify({"ok": True, "refresh": True, "log": "Analysis refreshed from the latest database contents."})


def _run_pull_job(reset_table: bool) -> None:
    global _is_pulling, _last_log
    try:
        json_path = _resolve_json_path()
        if not os.path.exists(json_path):
            _last_log = (
                "I couldn't find the input JSON file.\n\n"
                "Expected one of these:\n"
                "- ../module_2/llm_extend_applicant_data_liv.json\n"
                "- ../module_2/llm_extend_applicant_data.json\n\n"
                "If your file is somewhere else, set INSTRUCTOR_JSON_PATH to its full path."
            )
            return

        _last_log = f"Loading data from: {json_path}\n(reset={'yes' if reset_table else 'no'})\n"
        n = load_json_to_db(json_path, reset=reset_table)
        _last_log += f"\nDone. Loaded {n} records into PostgreSQL."
    except Exception as e:
        _last_log = f"Pull Data failed with an error:\n{e}"
    finally:
        _is_pulling = False


@app.post("/pull-data")
def pull_data():
    global _is_pulling, _last_log

    with _pull_lock:
        if _is_pulling:
            return jsonify({"ok": False, "error": "Pull Data is already running."}), 409

        _is_pulling = True
        _last_log = "Starting Pull Data…"

        reset_table = request.args.get("reset", "1").strip().lower() not in {"0", "false", "no"}

        t = threading.Thread(target=_run_pull_job, args=(reset_table,), daemon=True)
        t.start()

    return jsonify({"ok": True, "message": "Pull started. This page will update when it finishes."})


@app.post("/update_analysis")
def update_analysis_alias():
    return update_analysis()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
