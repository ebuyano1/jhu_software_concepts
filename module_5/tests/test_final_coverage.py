import pytest
from unittest.mock import patch, MagicMock

# IMPORTANT: We import 'app' exactly how conftest.py does.
# This ensures the test modifies the same STATE dictionary the Flask app uses.
import app

# -------------------------------------------------------------------
# Target: app.py (Lines 110-111 - Success path for /update-analysis)
# -------------------------------------------------------------------
def test_app_update_analysis_success(client):
    """
    Targets Lines 110-111.
    Forces is_pulling to False and verifies the returned status.
    """
    # Reset the 'real' state used by the Flask app
    app.STATE["is_pulling"] = False
    app.STATE["last_status"] = "Finished"
    
    with patch("app.get_analysis", return_value=[{"id": 1}]):
        resp = client.post("/update-analysis")
        
        assert resp.status_code == 200
        assert resp.json["ok"] is True
        # This will now match because we are using the correct module object
        assert resp.json["status"] == "Finished"

# -------------------------------------------------------------------
# Target: app.py (Lines 97-103 - Successful /pull-data trigger)
# -------------------------------------------------------------------
def test_app_pull_data_trigger(client):
    """Targets Lines 97-103. Checks if is_pulling is toggled to True."""
    app.STATE["is_pulling"] = False
    
    # Mock threading so we don't actually run the background scripts
    with patch("threading.Thread") as mock_thread:
        resp = client.post("/pull-data?reset=0")
        
        assert resp.status_code == 200
        # Check that the app correctly updated the shared state
        assert app.STATE["is_pulling"] is True
        assert mock_thread.return_value.start.called

# -------------------------------------------------------------------
# Target: app.py (Lines 68-69 - Unexpected Exception)
# -------------------------------------------------------------------
def test_run_pull_job_unexpected_error():
    """Targets Lines 68-69 by forcing a generic Exception."""
    # RuntimeError triggers the 'except Exception' block
    with patch("os.path.exists", side_effect=RuntimeError("Unexpected Crash")):
        app._run_pull_job(reset_table=False)
            
    assert "Unexpected Error: Unexpected Crash" in app.STATE["last_status"]
    assert app.STATE["is_pulling"] is False

# -------------------------------------------------------------------
# Auxiliary coverage for load_data.py and db.py (to keep 100%)
# -------------------------------------------------------------------
def test_normalize_row_various_inputs():
    from load_data import normalize_row
    # Line 90->98 (Empty URL)
    assert normalize_row({"overview_url": ""})["p_id"] is None
    # Line 106-107 (Invalid Date)
    assert normalize_row({"date_added": "not-a-date"})["date_added"] is None
    # Line 113-116 (Invalid GPA)
    assert normalize_row({"gpa": "invalid"})["gpa"] is None

def test_load_data_main_coverage():
    import load_data
    with patch("sys.argv", ["load_data.py", "--json", "f.json"]):
        with patch("load_data.load_json_to_db"):
            load_data.main()

def test_db_manual_dsn_coverage():
    import db
    with patch("psycopg.connect"):
        with db.get_conn(dsn="host=localhost"):
            pass