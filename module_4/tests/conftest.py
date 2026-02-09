"""
tests/conftest.py - Pytest Fixtures (Factory Pattern)
"""
import pytest
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import RealDictCursor
import os
import sys
import time  # Essential for the retry delay

# Ensure module_4 is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from db import get_db_dsn
from load_data import ensure_schema

TEST_DB_NAME = "gradcafe_test"

@pytest.fixture(scope="session")
def test_db():
    # 1. Connect to the 'postgres' maintenance database
    default_dsn = get_db_dsn(env_overrides={"PGDATABASE": "postgres"})
    conn = psycopg2.connect(default_dsn)
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    
    # 2. Heavy-Duty Retry Loop
    for i in range(10):
        try:
            # Forcibly terminate all other connections to the target DB
            cur.execute("""
                SELECT pg_terminate_backend(pid) 
                FROM pg_stat_activity 
                WHERE datname = %s AND pid <> pg_backend_pid();
            """, (TEST_DB_NAME,))
            
            # Attempt the drop
            cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME};")
            break  # Success!
        except psycopg2.errors.ObjectInUse:
            if i == 9: 
                raise  # Fail definitively after 10 tries
            # Increase sleep to 5 seconds to accommodate CI latency
            time.sleep(5) 
            
    # 3. Recreate the database
    cur.execute(f"CREATE DATABASE {TEST_DB_NAME};")
    
    cur.close()
    conn.close()
    
    return get_db_dsn(env_overrides={"PGDATABASE": TEST_DB_NAME})

@pytest.fixture(scope="function")
def db_cursor(test_db, mocker):
    mocker.patch("db.get_db_dsn", return_value=test_db)
    ensure_schema(reset=True)
    conn = psycopg2.connect(test_db)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    yield cur
    conn.rollback()
    cur.execute("TRUNCATE TABLE applicants;")
    conn.commit()
    cur.close()
    conn.close()

@pytest.fixture
def client(test_db, mocker):
    mocker.patch("db.get_db_dsn", return_value=test_db)
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client