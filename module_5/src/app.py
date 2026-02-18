"""
app.py — Module 3 Flask App (Factory Pattern)
"""
from __future__ import annotations

import os
import subprocess
import threading

from flask import Flask, jsonify, render_template, request, Blueprint

# Import specific logic
from load_data import load_json_to_db
from query_data import get_analysis

# Create a Blueprint to hold routes
bp = Blueprint('main', __name__)

# -------------------------------------------------------------------
# Shared State (Dictionary avoids global-statement and naming warnings)
# -------------------------------------------------------------------
STATE = {
    "lock": threading.Lock(),
    "is_pulling": False,
    "last_status": "Ready"
}

# -------------------------------------------------------------------
# Helper: Background Job
# -------------------------------------------------------------------
def _run_pull_job(reset_table: bool):
    """
    Executes the Scrape-Clean-Load pipeline in a background thread.
    """
    try:
        # STEP 1: SCRAPE
        scrape_script = "scrape.py"
        if os.path.exists(scrape_script):
            STATE["last_status"] = "Step 1/3: Scraping new data..."
            subprocess.run(["python", scrape_script], check=True)
        else:
            STATE["last_status"] = "Warning: scrape.py not found. Skipping scrape."

        # STEP 2: CLEAN
        clean_script = "clean.py"
        if os.path.exists(clean_script):
            STATE["last_status"] = "Step 2/3: Cleaning data with LLM..."
            subprocess.run(["python", clean_script], check=True)
        else:
            STATE["last_status"] = "Warning: clean.py not found. Skipping clean."

        # STEP 3: LOAD
        STATE["last_status"] = "Step 3/3: Loading data into PostgreSQL..."
        json_path = "llm_extend_applicant_data.json"
        if not os.path.exists(json_path):
            json_path = "llm_extend_applicant_data_liv.json"

        if os.path.exists(json_path):
            count = load_json_to_db(json_path, reset=reset_table)
            STATE["last_status"] = f"Success! Pipeline complete. Loaded {count} records."
        else:
            STATE["last_status"] = "Error: No JSON data file found."

    except subprocess.CalledProcessError as err:
        STATE["last_status"] = f"Subprocess Error: {err}"
    except IOError as err:
        STATE["last_status"] = f"File Error: {err}"
    except Exception as err:  # pylint: disable=broad-exception-caught
        STATE["last_status"] = f"Unexpected Error: {str(err)}"
    finally:
        with STATE["lock"]:
            STATE["is_pulling"] = False

# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------

@bp.route("/")
@bp.route("/analysis")
def index():
    """Renders the main analysis dashboard."""
    results = get_analysis()
    return render_template(
        "analysis.html",
        analysis=results,
        is_pulling=STATE["is_pulling"],
        last_status=STATE["last_status"]
    )

@bp.route("/pull-data", methods=["POST"])
def pull_data():
    """Triggers the background data pipeline."""
    with STATE["lock"]:
        if STATE["is_pulling"]:
            return jsonify({"ok": False, "msg": "Job already running"}), 409

        STATE["is_pulling"] = True
        STATE["last_status"] = "Starting..."
        reset = request.args.get("reset", "1") == "1"
        thread = threading.Thread(target=_run_pull_job, args=(reset,), daemon=True)
        thread.start()

    return jsonify({"ok": True, "msg": "Pull started"})

@bp.route("/update-analysis", methods=["POST"])
def update_analysis():
    """Returns the latest analysis data for AJAX updates."""
    if STATE["is_pulling"]:
        return jsonify({"ok": False, "msg": "Cannot update while Pull Data is running."}), 409
    data = get_analysis()
    return jsonify({"ok": True, "data": data, "status": STATE["last_status"]})

@bp.route("/status")
def status():
    """Returns the current background job status."""
    return jsonify({"pulling": STATE["is_pulling"], "status": STATE["last_status"]})

# -------------------------------------------------------------------
# Application Factory
# -------------------------------------------------------------------
def create_app(test_config=None):
    """Factory to create and configure the Flask app."""
    flask_app = Flask(__name__)

    if test_config:
        flask_app.config.update(test_config)

    # Register the blueprint containing all routes
    flask_app.register_blueprint(bp)

    return flask_app

if __name__ == "__main__":
    main_app = create_app()
    main_app.run(debug=False, port=5000)
