import pytest
from src.db import get_db_dsn

def test_get_db_dsn_with_overrides():
    """
    Explicitly triggers Line 19: env.update(env_overrides)
    to reach 100% coverage.
    """
    overrides = {"PGDATABASE": "coverage_test_db"}
    dsn = get_db_dsn(env_overrides=overrides)
    
    # Verify the override was applied to the DSN string
    assert "dbname=coverage_test_db" in dsn