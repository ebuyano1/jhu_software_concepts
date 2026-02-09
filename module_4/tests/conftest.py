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

# IMPORT create_app INSTEAD OF global app
from app import create_app
from db import get_db_dsn
from load_data import ensure_schema

TEST_DB_NAME = "gradcafe_test"

@pytest.fixture(scope="session")
def test_db():
    default_dsn = get_db_dsn(env_overrides={"PGDATABASE": "postgres"})
    conn = psycopg2.connect(default_dsn)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME};")
    cur.execute(f"CREATE DATABASE {TEST_DB_NAME};")
    cur.close()
    conn.close()

    test_dsn = get_db_dsn(env_overrides={"PGDATABASE": TEST_DB_NAME})
    yield test_dsn

    conn = psycopg2.connect(default_dsn)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute(f"""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = '{TEST_DB_NAME}'
        AND pid <> pg_backend_pid();
    """)
    cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME};")
    cur.close()
    conn.close()

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
    """
    Flask Test Client Fixture using the Factory Pattern.
    """
    mocker.patch("db.get_db_dsn", return_value=test_db)
    
    # Create the app using the factory
    app = create_app({"TESTING": True})
    
    with app.test_client() as client:
        yield client