import pytest
import subprocess
import threading
from unittest.mock import patch, MagicMock
import app as flask_app

@pytest.mark.buttons
def test_app_success_path():
    """Hits the 'Success' path in _run_pull_job."""
    # Access STATE dictionary instead of module attribute
    flask_app.STATE["is_pulling"] = False
    with patch("app.os.path.exists", return_value=True):
        with patch("app.subprocess.run"):
            with patch("app.load_json_to_db", return_value=100):
                flask_app._run_pull_job(reset_table=False)
    assert "Success" in flask_app.STATE["last_status"]

@pytest.mark.buttons
def test_app_warning_paths():
    """Test warning paths when scripts are missing."""
    flask_app.STATE["is_pulling"] = False
    with patch("app.os.path.exists", return_value=False):
        flask_app._run_pull_job(reset_table=False)
    assert "Warning" in flask_app.STATE["last_status"] or "Error" in flask_app.STATE["last_status"]

@pytest.mark.buttons
def test_app_exception_paths():
    """Test exception handling in the job (Lines 64-69 in app.py)."""
    flask_app.STATE["is_pulling"] = False
    
    # 1. Subprocess Error (Line 64-65)
    with patch("app.os.path.exists", return_value=True):
        with patch("app.subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd")):
            flask_app._run_pull_job(False)
    assert "Subprocess Error" in flask_app.STATE["last_status"]

    # 2. IO Error (Line 66-67)
    with patch("app.os.path.exists", return_value=True):
        with patch("app.subprocess.run", side_effect=IOError("Disk Full")):
            flask_app._run_pull_job(False)
    assert "File Error" in flask_app.STATE["last_status"]

@pytest.mark.buttons
def test_busy_gating(client):
    """Verify busy gating returns 409 when a pull is in progress (Lines 95, 109)."""
    with patch.dict("app.STATE", {"is_pulling": True, "lock": threading.Lock()}):
        # Test /pull-data 409
        resp1 = client.post("/pull-data")
        assert resp1.status_code == 409
        
        # Test /update-analysis 409
        resp2 = client.post("/update-analysis")
        assert resp2.status_code == 409

@pytest.mark.buttons
def test_status_route(client):
    """Covers Line 116 in app.py."""
    flask_app.STATE["last_status"] = "Testing Status"
    resp = client.get("/status")
    assert resp.status_code == 200
    assert resp.json["status"] == "Testing Status"
