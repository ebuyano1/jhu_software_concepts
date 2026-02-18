import pytest
import json
import os
from unittest.mock import patch, MagicMock, mock_open
from load_data import load_json, load_rows
import db

@pytest.mark.db
def test_load_json_success():
    """Hits Lines 167-172 in load_data.py."""
    fake_json = '[{"overview_url": "test", "university": "JHU"}]'
    # Mock exists and open to bypass the 'basename' path restriction
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=fake_json)):
            data = load_json("any_path/data.json")
            assert len(data) == 1
            assert data[0]["university"] == "JHU"

@pytest.mark.db
def test_load_json_not_a_list():
    """Hits Line 171: ValueError for non-list JSON."""
    fake_json = '{"not": "a list"}'
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=fake_json)):
            with pytest.raises(ValueError, match="Expected a JSON list"):
                load_json("bad.json")

@pytest.mark.db
def test_db_rollback_path():
    """Verifies that DB rollback is called on error (Lines 70-71 in db.py)."""
    mock_conn = MagicMock()
    # Ensure the context manager returns the mock connection
    mock_conn.__enter__.return_value = mock_conn
    
    with patch("psycopg.connect", return_value=mock_conn):
        with pytest.raises(ValueError, match="Force Rollback"):
            with db.get_cursor():
                raise ValueError("Force Rollback")
    
    # Check that rollback was called on the connection
    mock_conn.rollback.assert_called_once()
