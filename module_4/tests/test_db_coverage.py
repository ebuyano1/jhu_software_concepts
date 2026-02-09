import pytest
from src.db import get_db_dsn
from src.load_data import ensure_schema


def test_get_db_dsn_with_overrides():
    """
    Explicitly triggers Line 19 in db.py: env.update(env_overrides)
    to reach 100% coverage.
    """
    overrides = {"PGDATABASE": "coverage_test_db"}
    dsn = get_db_dsn(env_overrides=overrides)
    
    # Verify the override was applied to the DSN string
    assert "dbname=coverage_test_db" in dsn

def test_ensure_schema_table_already_exists(capsys):
    """
    Triggers the print statement in load_data.py to reach 100% coverage.
    """
    # 1. Ensure table exists first
    ensure_schema(reset=True)
    
    # 2. Call again without reset to trigger the success/exists message
    ensure_schema(reset=False)
    
    # 3. Capture stdout to confirm the line was reached
    captured = capsys.readouterr()
    assert "already exists" in captured.out