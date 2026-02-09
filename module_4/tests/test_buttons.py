import pytest
from unittest.mock import patch
import app as flask_app

@pytest.mark.buttons
def test_app_success_path():
    """Hits Line 57: The 'Success' path in _run_pull_job."""
    flask_app._is_pulling = False
    with patch("app.os.path.exists", return_value=True):
        with patch("app.subprocess.run"):
            with patch("app.load_json_to_db", return_value=100):
                flask_app._run_pull_job(reset_table=False)
    assert "Success" in flask_app._last_status

@pytest.mark.buttons
def test_app_warning_paths():
    """Test warning paths when scripts are missing."""
    flask_app._is_pulling = False
    with patch("app.os.path.exists", return_value=False):
        flask_app._run_pull_job(reset_table=False)
    assert "Warning" in flask_app._last_status or "Error" in flask_app._last_status

@pytest.mark.buttons
def test_app_exception_path():
    """Test exception handling in the job."""
    flask_app._is_pulling = False
    with patch("app.os.path.exists", return_value=True):
        with patch("app.subprocess.run", side_effect=Exception("Crash Test")):
            flask_app._run_pull_job(reset_table=False)
    assert "Error: Crash Test" in flask_app._last_status

@pytest.mark.buttons
def test_busy_gating(client):
    """
    REQUIRED: Verify busy gating returns 409 when a pull is in progress.
    """
    # Force the app to think it is busy
    with patch("app._is_pulling", True):
        # Try to trigger an update
        response = client.post("/update-analysis")
        assert response.status_code == 409
        # FIXED: Check for 'ok': False instead of 'busy' key
        assert response.json['ok'] is False
        assert "Cannot update" in response.json['msg']
        
        # Try to trigger a pull
        response = client.post("/pull-data")
        assert response.status_code == 409

@pytest.mark.buttons
def test_app_routes_coverage(client):
    """
    Covers the missing logic in app.py:
    1. /status route (Line 106)
    2. /update-analysis SUCCESS path (Lines ~103)
    3. /pull-data SUCCESS path (Lines 89-95)
    """
    import app as flask_app
    
    # 1. Cover /status
    resp = client.get("/status")
    assert resp.status_code == 200
    assert "pulling" in resp.json

    # 2. Cover /update-analysis (Success Path)
    # Ensure app thinks it is NOT pulling
    with patch("app._is_pulling", False):
        with patch("app.get_analysis", return_value=[]):
            resp = client.post("/update-analysis")
            assert resp.status_code == 200
            assert resp.json["ok"] is True

    # 3. Cover /pull-data (Success Path) - This is Lines 89-95
    # We mock threading.Thread so we don't actually spawn a thread
    with patch("app._is_pulling", False):
        with patch("app.threading.Thread") as mock_thread:
            resp = client.post("/pull-data")
            
            assert resp.status_code == 200
            assert resp.json["ok"] is True
            # Verify the thread was started (hitting line 94)
            mock_thread.return_value.start.assert_called_once()