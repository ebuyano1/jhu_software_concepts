"""
app.py (Module 3) — Flask dashboard + Pull Data + Update Analysis

From module 2:
  - ../module_2/scrape.py produces applicant_data.json
  - ../module_2/clean.py produces llm_extend_applicant_data.json

Pull Data:
  1) Runs scrape.py, clean.py 
  2) Loads ../module_2/llm_extend_applicant_data.json and then uses upserts to put data into PostgreSQL

Update Analysis behavior:
  - Re-Calculcates the analysis if Pull Data is not running .
"""

from __future__ import annotations

import os
import sys
import time
import threading
import subprocess
from typing import Optional, Dict, Any

from flask import Flask, jsonify, redirect, render_template, request, url_for

from query_data import get_analysis
from load_data import load_json, load_rows

app = Flask(__name__)

# -----------------------------
# Thread safe pull state
# -----------------------------
_pull_lock = threading.Lock()
_is_pulling = False
_pull_last_log = ""
_pull_last_loaded = 0
_pull_last_finished_at: Optional[float] = None


def _wants_json() -> bool:
    accept = request.headers.get("Accept", "")
    return "application/json" in accept.lower()


def _set_pull_state(is_pulling: bool, log: str = "", loaded: int = 0) -> None:
    global _is_pulling, _pull_last_log, _pull_last_loaded, _pull_last_finished_at
    with _pull_lock:
        _is_pulling = is_pulling
        if log:
            _pull_last_log = log
        if loaded:
            _pull_last_loaded = loaded
        if not is_pulling:
            _pull_last_finished_at = time.time()


def _get_pull_state() -> Dict[str, Any]:
    with _pull_lock:
        return {
            "is_pulling": _is_pulling,
            "last_log": _pull_last_log,
            "last_loaded": _pull_last_loaded,
            "last_finished_at": _pull_last_finished_at,
        }


def _run_module2_pipeline() -> str:
    """Run Module 2 scrape + clean. Return path to cleaned JSON."""
    # Allow overrides if you ever move files
    mod2_dir = os.getenv("MODULE2_DIR", os.path.join("..", "module_2"))
    scrape_script = os.getenv("MODULE2_SCRAPE", os.path.join(mod2_dir, "scrape.py"))
    clean_script = os.getenv("MODULE2_CLEAN", os.path.join(mod2_dir, "clean.py"))
    cleaned_json = os.getenv("MODULE2_CLEANED_JSON", os.path.join(mod2_dir, "llm_extend_applicant_data.json"))

    # Run scrape.py if present
    if os.path.exists(scrape_script):
        subprocess.run([sys.executable, scrape_script], check=True)
    else:
        # Not fatal if applicant_data.json is there from a prior run
        pass

    # Run clean.py if present
    if os.path.exists(clean_script):
        subprocess.run([sys.executable, clean_script], check=True)
    else:
        # Not fatal if llm_extend_applicant_data.json is there from a prior run
        pass

    return cleaned_json


def _pull_job() -> None:
    try:
        t0 = time.time()
        cleaned_json = _run_module2_pipeline()

        if not os.path.exists(cleaned_json):
            raise FileNotFoundError(
                f"Cleaned JSON not found at '{cleaned_json}'. "
                "Run Module 2 (scrape.py then clean.py), or set MODULE2_* env vars."
            )

        rows = load_json(cleaned_json)
        loaded = load_rows(rows)
        elapsed = round(time.time() - t0, 2)

        _set_pull_state(
            is_pulling=False,
            log=f"Pull Data complete. Loaded/updated {loaded} rows from {cleaned_json} in {elapsed:.2f}s.",
            loaded=loaded,
        )
    except Exception as e:
        _set_pull_state(is_pulling=False, log=f"Pull Data failed: {e}")


@app.get("/")
def root():
    return redirect(url_for("analysis"))


@app.get("/analysis")
def analysis():
    rows = get_analysis()
    pull_state = _get_pull_state()
    return render_template("analysis.html", rows=rows, pull_state=pull_state)


@app.get("/pull-status")
def pull_status():
    return jsonify(ok=True, **_get_pull_state())


@app.post("/pull-data")
def pull_data():
    st = _get_pull_state()
    if st["is_pulling"]:
        msg = "Pull Data is already running. Please wait until it completes."
        if _wants_json():
            return jsonify(ok=False, error=msg, **st), 409
        return redirect(url_for("analysis"))

    _set_pull_state(True, log="Pull Data started…")
    th = threading.Thread(target=_pull_job, daemon=True)
    th.start()

    if _wants_json():
        return jsonify(ok=True, started=True, message="Pull Data started.", **_get_pull_state())
    return redirect(url_for("analysis"))


@app.post("/update-analysis")
def update_analysis():
    st = _get_pull_state()
    if st["is_pulling"]:
        msg = "Update Analysis is disabled while Pull Data is running."
        if _wants_json():
            return jsonify(ok=False, error=msg, **st), 409
        return redirect(url_for("analysis"))

    start = time.time()
    _ = get_analysis()
    elapsed = round(time.time() - start, 2)

    if _wants_json():
        return jsonify(ok=True, refresh=True, log=f"Analysis recomputed in {elapsed:.2f}s.", **_get_pull_state())
    return redirect(url_for("analysis"))


@app.post("/update_analysis")
def update_analysis_alias():
    return update_analysis()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
