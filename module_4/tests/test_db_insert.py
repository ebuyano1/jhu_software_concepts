import pytest
from unittest.mock import patch, MagicMock
from load_data import load_rows, normalize_row, load_json, ensure_schema
import db

# -------------------------------------------------------------------
# HAPPY PATH (Requirements: Insert, Idempotency, Simple Query)
# -------------------------------------------------------------------
SAMPLE_ROW = {
    "overview_url": "https://gradcafe.com/result/1",
    "university": "Test U",
    "program": "CS",
    "date_added": "15 Feb 2025"
}

@pytest.mark.db
def test_insert_on_pull(db_cursor):
    """Test insert on pull: Before empty, After rows exist."""
    db_cursor.execute("SELECT COUNT(*) as count FROM applicants")
    assert db_cursor.fetchone()['count'] == 0
    
    load_rows([SAMPLE_ROW])
    
    db_cursor.execute("SELECT COUNT(*) as count FROM applicants")
    assert db_cursor.fetchone()['count'] == 1
    
    db_cursor.execute("SELECT university FROM applicants")
    assert db_cursor.fetchone()['university'] == "Test U"

@pytest.mark.db
def test_idempotency(db_cursor):
    """Test that duplicate rows do not create duplicates in database."""
    load_rows([SAMPLE_ROW])
    load_rows([SAMPLE_ROW]) # Insert same data again
    
    db_cursor.execute("SELECT COUNT(*) as count FROM applicants")
    assert db_cursor.fetchone()['count'] == 1

@pytest.mark.db
def test_simple_query_function(db_cursor):
    """Query data returns dict with expected keys."""
    load_rows([SAMPLE_ROW])
    db_cursor.execute("SELECT * FROM applicants WHERE p_id = 1")
    row = db_cursor.fetchone()
    assert "university" in row
    assert "program" in row
    assert "p_id" in row

# -------------------------------------------------------------------
# EDGE CASES & COVERAGE (Merged from previous helper files)
# -------------------------------------------------------------------
@pytest.mark.db
def test_load_data_normalization_logic():
    """Tests data cleaning edge cases (dates, floats)."""
    # 1. Date Parse Exception
    row_date_retry = {"overview_url": "u1", "date_added": "February 20, 2025"}
    norm = normalize_row(row_date_retry)
    assert norm["date_added"] is not None

    # 2. Float ValueError
    row_bad_float = {"overview_url": "u2", "gpa": "Invalid"}
    norm = normalize_row(row_bad_float)
    assert norm["gpa"] is None

    # 3. Float Empty Check
    row_empty_float = {"overview_url": "u3", "gpa": ""}
    norm = normalize_row(row_empty_float)
    assert norm["gpa"] is None

@pytest.mark.db
def test_load_json_file_errors(tmp_path):
    """Tests FileNotFoundError and ValueError for bad JSON."""
    # Case A: Missing File
    with pytest.raises(FileNotFoundError):
        load_json("ghost_file_123.json")

    # Case B: Bad Structure (Dict not List)
    p = tmp_path / "bad.json"
    p.write_text('{"not": "a list"}', encoding="utf-8")
    with pytest.raises(ValueError):
        load_json(str(p))

@pytest.mark.db
def test_load_data_skip_logic():
    """Tests skipping rows with missing IDs."""
    bad_row = {"overview_url": "https://gradcafe.com/result/no_numbers"} 
    count = load_rows([bad_row])
    assert count == 0

@pytest.mark.db
def test_ensure_schema_generic_exception():
    """Forces ensure_schema to raise a generic exception (DB Crash)."""
    with patch("load_data.get_cursor") as mock_get_cur:
        mock_cur = mock_get_cur.return_value.__enter__.return_value
        mock_cur.execute.side_effect = Exception("Critical DB Failure")
        
        with pytest.raises(Exception, match="Critical DB Failure"):
            ensure_schema(reset=False)

@pytest.mark.db
def test_db_rollback_path():
    """Verifies that DB rollback is called on error."""
    mock_conn = MagicMock()
    with patch("db.psycopg2.connect", return_value=mock_conn):
        with pytest.raises(ValueError):
            with db.get_cursor():
                raise ValueError("Force Rollback")
    mock_conn.rollback.assert_called()

@pytest.mark.db
def test_load_data_branch_coverage():
    """
    Nuclear option to hit every branch in normalize_row.
    Uses REAL URL formats to pass the ID check, but MESSY data to hit edge cases.
    """
    from load_data import normalize_row
    
    # 1. Force Date Parsing Branch (Lines ~89-98)
    # Case A: Good Format 1 ("15 Feb 2025") -> Handled by normal tests
    # Case B: Good Format 2 ("February 15, 2025") -> Forces the 'except ValueError' path
    row_alt_date = {
        "overview_url": "https://www.thegradcafe.com/result/12345",
        "date_added": "February 15, 2025"  # Valid, but triggers the "retry" logic
    }
    norm = normalize_row(row_alt_date)
    assert norm['date_added'] is not None

    # Case C: Garbage Date -> Forces the final 'except' to return None
    row_bad_date = {
        "overview_url": "https://www.thegradcafe.com/result/12346",
        "date_added": "Not A Date"         # Invalid, triggers the final failure
    }
    norm = normalize_row(row_bad_date)
    assert norm['date_added'] is None

    # 2. Force Float Conversion Branch (Lines ~102-110)
    # Case A: Empty String -> Forces 'if not value:' check
    row_empty_gpa = {
        "overview_url": "https://www.thegradcafe.com/result/12347", 
        "gpa": ""                          # Empty, triggers early None return
    }
    norm = normalize_row(row_empty_gpa)
    assert norm['gpa'] is None

    # Case B: Garbage String -> Forces 'except ValueError'
    row_bad_gpa = {
        "overview_url": "https://www.thegradcafe.com/result/12348", 
        "gpa": "Four Point Oh"             # Invalid, triggers exception catch
    }
    norm = normalize_row(row_bad_gpa)
    assert norm['gpa'] is None

@pytest.mark.db
def test_load_json_success(tmp_path):
    """
    Runs the REAL load_json function with a REAL valid file.
    Hits Line 168 (return data).
    """
    from load_data import load_json
    
    # 1. Create a valid temporary JSON file
    p = tmp_path / "valid.json"
    p.write_text('[{"id": 1, "name": "test"}]', encoding="utf-8")
    
    # 2. Call the real function
    data = load_json(str(p))
    
    # 3. Verify it worked
    assert len(data) == 1
    assert data[0]["id"] == 1

@pytest.mark.db
def test_load_data_date_retry_logic():
    """
    Forces the 'except ValueError' path in date parsing (Lines 89-98).
    This covers the missing branch in load_data.py.
    """
    from load_data import normalize_row
    
    # 1. Provide a date format that FAILS the first try ("%d %b %Y")
    #    but PASSES the second try ("%B %d, %Y").
    #    First try expects: "15 Feb 2025"
    #    We give: "February 15, 2025" -> triggers the except block
    row_retry_date = {
        "overview_url": "https://www.thegradcafe.com/result/99999",
        "date_added": "February 15, 2025"
    }
    
    norm = normalize_row(row_retry_date)
    
    # If the logic works, we get a valid date object back
    assert norm['date_added'] is not None

@pytest.mark.db
def test_load_data_bad_url_pattern():
    """
    Hits the branch where 'url' exists but does NOT match the regex.
    Line 89 -> 98 (skips p_id assignment).
    """
    from load_data import normalize_row
    
    # URL exists, but has no '/result/123' pattern
    row_bad_url = {
        "overview_url": "https://www.thegradcafe.com/survey/index.php",
        "date_added": "15 Feb 2025"
    }
    
    # 1. Run the function
    norm = normalize_row(row_bad_url)
    
    # 2. FIX: Check that p_id is None (the dictionary itself is NOT None)
    assert norm is not None
    assert norm["p_id"] is None

@pytest.mark.db
def test_load_data_empty_url():
    """
    Hits the branch where 'url' is empty.
    Forces the 'if url:' check (Line 89) to evaluate to False.
    """
    from load_data import normalize_row
    
    # URL is empty string
    row_empty_url = {
        "overview_url": "",
        "university": "Test U"
    }
    
    norm = normalize_row(row_empty_url)
    
    # Expectation: p_id is None, and we didn't crash
    assert norm["p_id"] is None
    assert norm["university"] == "Test U"

@pytest.mark.db
def test_db_dsn_full_env_vars():
    """
    Hits lines 25-31 in db.py by forcing every environment variable check to True.
    CRITICAL: We must ensure DATABASE_URL is NOT set, otherwise the code 
    returns early and skips the logic we want to test.
    """
    from db import get_db_dsn
    import os
    from unittest.mock import patch

    # 1. Define our fake variables
    env_vars = {
        "PGUSER": "custom_user",
        "PGPASSWORD": "custom_password",
        "PGHOST": "custom_host",
        "PGPORT": "5432",
        "PGDATABASE": "custom_db"
    }

    # 2. Use patch.dict with clear=True
    # clear=True wipes out existing real env vars (like DATABASE_URL)
    # so the function is forced to build the DSN from scratch using our fake values.
    with patch.dict(os.environ, env_vars, clear=True):
        dsn = get_db_dsn()
        
        # 3. Verify the fallback logic ran
        assert "user=custom_user" in dsn
        assert "password=custom_password" in dsn
        assert "host=custom_host" in dsn
        assert "port=5432" in dsn
        assert "dbname=custom_db" in dsn

@pytest.mark.db
def test_db_custom_dsn_branch():
    """
    Calls get_conn() with a specific DSN to hit the 'else' branch 
    of 'if dsn is None'. (Branch 45->48 in db.py)
    """
    from db import get_conn
    from unittest.mock import patch

    # Mock psycopg2.connect so we don't actually try to connect to a fake URL
    with patch("db.psycopg2.connect") as mock_pg:
        # Pass a custom DSN string
        fake_dsn = "postgres://user:pass@localhost:5432/testdb"
        
        # This triggers the code path where dsn is NOT None
        with get_conn(dsn=fake_dsn) as conn:
            pass
        
        # Verify it passed our DSN to the connector
        mock_pg.assert_called_with(fake_dsn)