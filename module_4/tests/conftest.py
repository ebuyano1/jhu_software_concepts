"""
tests/conftest.py - Pytest Fixtures (Factory Pattern)
"""
import pytest
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import RealDictCursor
import os
import sys

# Ensure module_4 is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from db import get_db_dsn
from load_data import ensure_schema

TEST_DB_NAME = "gradcafe_test"

import time  # Add this at the top with other imports

@pytest.fixture(scope="session")
def test_db():
    # 1. Connect to the 'postgres' maintenance database first
    # This allows us to drop 'gradcafe_test' while not being "inside" it.
    default_dsn = get_db_dsn(env_overrides={"PGDATABASE": "postgres"})
    conn = psycopg2.connect(default_dsn)
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    
    # 2. Forcefully terminate all other connections to gradcafe_test
    # This clears any "ObjectInUse" blocks caused by zombie processes.
    cur.execute("""
        SELECT pg_terminate_backend(pid) 
        FROM pg_stat_activity 
        WHERE datname = %s AND pid <> pg_backend_pid();
    """, (TEST_DB_NAME,))
    
    # 3. Now it is safe to drop and recreate the test database
    cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME};")
    cur.execute(f"CREATE DATABASE {TEST_DB_NAME};")
    
    cur.close()
    conn.close()
    
    # Return the DSN for the newly created test database
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
    app = create_app({"TESTING": True}) [cite: 8]
    with app.test_client() as client:
        yield client