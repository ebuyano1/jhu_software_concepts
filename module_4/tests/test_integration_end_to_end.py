import pytest
from unittest.mock import patch, MagicMock
import load_data

@pytest.mark.integration
def test_load_data_main_exception(mocker):
    """Tests the main entry point exception handling."""
    mocker.patch("sys.argv", ["load_data.py", "--reset"])
    mocker.patch.object(load_data, "load_json_to_db", side_effect=Exception("Main Crash"))
    
    with pytest.raises(Exception, match="Main Crash"):
        load_data.main()

@pytest.mark.integration
def test_real_load_process_integration(capsys):
    """
    Simulates a full load process using real logic (mocking only I/O).
    """
    dummy_data = [
        {"overview_url": "https://gradcafe.com/result/12345", "university": "Good U"},
        {"overview_url": "https://gradcafe.com/result/bad_url", "university": "Bad U"}
    ]

    with patch.object(load_data, "load_json", return_value=dummy_data):
        with patch.object(load_data, "get_cursor") as mock_cursor:
            mock_cursor.return_value.__enter__.return_value = MagicMock()
            with patch.object(load_data, "ensure_schema"):
                result = load_data.load_json_to_db("dummy_path.json")

    assert result == 1
    captured = capsys.readouterr()
    assert "Skipped 1 rows" in captured.out