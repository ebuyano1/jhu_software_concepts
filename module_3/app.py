"""
app.py — Module 3 Flask App (Database Queries + Analysis)

Features:
- /analysis: Displays the stylized dashboard.
- /pull-data: Background thread to run Scrape -> Clean -> Load.
- /update-analysis: Refreshes the SQL results.
- Locking: Prevents 'Update Analysis' from running if 'Pull Data' is active.
"""

from __future__ import annotations

import os
import subprocess
import threading
import time
from typing import Any, Dict, List

from flask import Flask, jsonify, render_template, request

# Import our specific logic
from load_data import load_json_to_db
from query_data import get_analysis

app = Flask(__name__)

# -------------------------------------------------------------------
# Shared State & Locking
# -------------------------------------------------------------------
_pull_lock = threading.Lock()
_is_pulling: bool = False
_last_status: str = "Ready"

# -------------------------------------------------------------------
# Helper: The Background Job
# -------------------------------------------------------------------
def _run_pull_job(reset_table: bool):
    global _is_pulling, _last_status
    try:
        # --- STEP 1: SCRAPE ---
        scrape_script = "scrape.py"
        if os.path.exists(scrape_script):
            _last_status = "Step 1/3: Scraping new data..."
            subprocess.run(["python", scrape_script], check=True)
        else:
            _last_status = "Warning: scrape.py not found. Skipping scrape."

        # --- STEP 2: CLEAN (LLM) ---
        clean_script = "clean.py"
        # The scraper typically outputs 'applicant_data.json'
        # The cleaner typically outputs 'llm_extend_applicant_data.json'
        if os.path.exists(clean_script):
            _last_status = "Step 2/3: Cleaning data with LLM..."
            subprocess.run(["python", clean_script], check=True)
        else:
            _last_status = "Warning: clean.py not found. Skipping clean."
        
        # --- STEP 3: LOAD INTO DB ---
        _last_status = "Step 3/3: Loading data into PostgreSQL..."
        
        # Priority 1: The output from clean.py (freshly made)
        json_path = "llm_extend_applicant_data.json" 
        
        # Priority 2: The original provided file (fallback)
        if not os.path.exists(json_path):
             json_path = "llm_extend_applicant_data_liv.json"

        if os.path.exists(json_path):
            n = load_json_to_db(json_path, reset=reset_table)
            _last_status = f"Success! Pipeline complete. Loaded {n} records."
        else:
            _last_status = "Error: No JSON data file found (checked new and old)."
            
    except Exception as e:
        _last_status = f"Error: {str(e)}"
    finally:
        with _pull_lock:
            _is_pulling = False

# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------

@app.route("/")
@app.route("/analysis")
def index():
    """Renders the main dashboard."""
    # Fetch the latest results from PostgreSQL
    results = get_analysis()
    
    return render_template(
        "analysis.html",
        analysis=results,
        is_pulling=_is_pulling,
        last_status=_last_status
    )

@app.route("/pull-data", methods=["POST"])
def pull_data():
    """Starts the background scraping/loading job."""
    global _is_pulling, _last_status

    with _pull_lock:
        if _is_pulling:
            return jsonify({"ok": False, "msg": "Job already running"}), 409

        _is_pulling = True
        _last_status = "Starting..."
        
        # Check if user wants to reset the table (default: yes)
        reset = request.args.get("reset", "1") == "1"

        # Start thread
        thread = threading.Thread(target=_run_pull_job, args=(reset,), daemon=True)
        thread.start()

    return jsonify({"ok": True, "msg": "Pull started"})

@app.route("/update-analysis", methods=["POST"])
def update_analysis():
    """Refreshes the data."""
    if _is_pulling:
        return jsonify({
            "ok": False, 
            "msg": "Cannot update while Pull Data is running."
        }), 409

    data = get_analysis()
    return jsonify({"ok": True, "data": data, "status": _last_status})

@app.route("/status")
def status():
    """Lightweight endpoint for frontend to check job status."""
    return jsonify({"pulling": _is_pulling, "status": _last_status})

if __name__ == "__main__":
    app.run(debug=True, port=5000)