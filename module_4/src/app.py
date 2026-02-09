"""
app.py — Module 3 Flask App (Factory Pattern)
"""
from __future__ import annotations

import os
import subprocess
import threading
from typing import Any, Dict, List

from flask import Flask, jsonify, render_template, request, Blueprint

# Import specific logic
from load_data import load_json_to_db
from query_data import get_analysis

# Create a Blueprint to hold routes (replaces global 'app' for routing)
bp = Blueprint('main', __name__)

# -------------------------------------------------------------------
# Shared State & Locking (Module-level globals are fine here)
# -------------------------------------------------------------------
_pull_lock = threading.Lock()
_is_pulling: bool = False
_last_status: str = "Ready"

# -------------------------------------------------------------------
# Helper: Background Job
# -------------------------------------------------------------------
def _run_pull_job(reset_table: bool):
    global _is_pulling, _last_status
    try:
        # STEP 1: SCRAPE
        scrape_script = "scrape.py"
        if os.path.exists(scrape_script):
            _last_status = "Step 1/3: Scraping new data..."
            subprocess.run(["python", scrape_script], check=True)
        else:
            _last_status = "Warning: scrape.py not found. Skipping scrape."

        # STEP 2: CLEAN
        clean_script = "clean.py"
        if os.path.exists(clean_script):
            _last_status = "Step 2/3: Cleaning data with LLM..."
            subprocess.run(["python", clean_script], check=True)
        else:
            _last_status = "Warning: clean.py not found. Skipping clean."
        
        # STEP 3: LOAD
        _last_status = "Step 3/3: Loading data into PostgreSQL..."
        json_path = "llm_extend_applicant_data.json" 
        if not os.path.exists(json_path):
             json_path = "llm_extend_applicant_data_liv.json"

        if os.path.exists(json_path):
            n = load_json_to_db(json_path, reset=reset_table)
            _last_status = f"Success! Pipeline complete. Loaded {n} records."
        else:
            _last_status = "Error: No JSON data file found."
            
    except Exception as e:
        _last_status = f"Error: {str(e)}"
    finally:
        with _pull_lock:
            _is_pulling = False

# -------------------------------------------------------------------
# Routes (Registered on Blueprint 'bp', not 'app')
# -------------------------------------------------------------------

@bp.route("/")
@bp.route("/analysis")
def index():
    results = get_analysis()
    return render_template(
        "analysis.html",
        analysis=results,
        is_pulling=_is_pulling,
        last_status=_last_status
    )

@bp.route("/pull-data", methods=["POST"])
def pull_data():
    global _is_pulling, _last_status
    with _pull_lock:
        if _is_pulling:
            return jsonify({"ok": False, "msg": "Job already running"}), 409

        _is_pulling = True
        _last_status = "Starting..."
        reset = request.args.get("reset", "1") == "1"
        thread = threading.Thread(target=_run_pull_job, args=(reset,), daemon=True)
        thread.start()

    return jsonify({"ok": True, "msg": "Pull started"})

@bp.route("/update-analysis", methods=["POST"])
def update_analysis():
    if _is_pulling:
        return jsonify({"ok": False, "msg": "Cannot update while Pull Data is running."}), 409
    data = get_analysis()
    return jsonify({"ok": True, "data": data, "status": _last_status})

@bp.route("/status")
def status():
    return jsonify({"pulling": _is_pulling, "status": _last_status})

# -------------------------------------------------------------------
# Application Factory
# -------------------------------------------------------------------
def create_app(test_config=None):
    """Factory to create and configure the Flask app."""
    app = Flask(__name__)
    
    if test_config:
        app.config.update(test_config)

    # Register the blueprint containing all routes
    app.register_blueprint(bp)
    
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)