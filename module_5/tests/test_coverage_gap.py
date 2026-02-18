import os
import pytest
import json
from load_data import normalize_row, load_json

@pytest.mark.coverage
def test_normalize_row_logic_coverage():
    """
    Targets Lines 90-98 in load_data.py.
    Verifies regex extraction of p_id and date parsing.
    """
    raw_data = {
        "overview_url": "https://www.thegradcafe.com/result/987654",
        "date_added": "20 Feb 2025",
        "university": "Test University"
    }
    
    normalized = normalize_row(raw_data)
    
    # This hits the 'if match:' branch (Line 94-95)
    assert normalized["p_id"] == 987654
    # This hits the date parsing loop (Line 104+)
    assert normalized["date_added"].year == 2025

@pytest.mark.coverage
def test_load_json_path_fallback_coverage(tmp_path):
    """
    Targets the path fallback logic in load_json.
    Hits the branch where the full path doesn't exist, 
    but the basename does.
    """
    # 1. Create a dummy file in the CURRENT working directory
    # (Since load_json uses os.path.exists on the current dir)
    filename = "coverage_dummy.json"
    content = [{"overview_url": "test/1", "university": "U"}]
    
    with open(filename, "w") as f:
        json.dump(content, f)

    try:
        # 2. Call load_json with a 'fake' directory prefix.
        # This forces os.path.exists(path) to be False, 
        # but os.path.exists(basename) to be True.
        fake_path = os.path.join("non_existent_folder", filename)
        data = load_json(fake_path)
        
        assert len(data) == 1
        assert data[0]["university"] == "U"
    finally:
        # Cleanup the file from your root
        if os.path.exists(filename):
            os.remove(filename)

@pytest.mark.coverage
def test_load_json_file_not_found_exception():
    """
    Targets the 'raise FileNotFoundError' line.
    """
    with pytest.raises(FileNotFoundError):
        # Use a filename that definitely doesn't exist
        load_json("this_file_is_nowhere_to_be_found_12345.json")
