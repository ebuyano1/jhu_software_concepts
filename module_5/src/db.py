"""
db.py - Database Connection Manager (Software Assurance Edition)
"""
import os
from contextlib import contextmanager
from typing import Dict, Generator, Optional
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

# Load the .env file into the system environment
load_dotenv()

def get_db_dsn(env_overrides: Optional[Dict[str, str]] = None) -> str:
    """
    Builds a PostgreSQL DSN using environment variables or optional overrides.
    
    :param env_overrides: A dictionary of environment variables to override.
    :return: A PostgreSQL DSN connection string.
    """
    # Use system environment as base
    env = os.environ.copy()

    # Apply overrides if provided (triggers line for coverage)
    if env_overrides:
        env.update(env_overrides)

    # To fix the AssertionError, we prioritize standard PG variables
    # (PGDATABASE, etc.) which the tests use for overrides.
    host = env.get("PGHOST", env.get("DB_HOST"))
    port = env.get("PGPORT", env.get("DB_PORT"))
    user = env.get("PGUSER", env.get("DB_USER"))
    password = env.get("PGPASSWORD", env.get("DB_PASSWORD"))
    dbname = env.get("PGDATABASE", env.get("DB_NAME"))

    # Build the connection string
    return (
        f"host={host} "
        f"port={port} "
        f"user={user} "
        f"password={password} "
        f"dbname={dbname}"
    )

@contextmanager
def get_conn(dsn: Optional[str] = None) -> Generator[psycopg.Connection, None, None]:
    """
    Context manager that yields a PostgreSQL connection.
    
    :param dsn: Optional manual DSN string to bypass environment lookup.
    """
    connection_string = dsn if dsn else get_db_dsn()
    with psycopg.connect(connection_string) as conn:
        yield conn

@contextmanager
def get_cursor(dict_rows: bool = False) -> Generator[psycopg.Cursor, None, None]:
    """
    Context manager that yields a database cursor.
    
    :param dict_rows: If True, returns rows as dictionaries.
    """
    with get_conn() as conn:
        row_factory = dict_row if dict_rows else None
        cur = conn.cursor(row_factory=row_factory)
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
