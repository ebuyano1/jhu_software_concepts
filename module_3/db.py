"""
This module encapsulates how we connect to PostgreSQL so that the rest of 
our codebase does not need to learn the details of how to connect.
Connections are configured via environment variables for security purposes, 
so that sensitive credentials like passwords never touch source control.


"""

import os
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables from a .env file if present.
# This is especially useful for local development so DATABASE_URL
# does not need to be set manually in the shell.
from dotenv import load_dotenv
load_dotenv()


def get_db_dsn() -> str:
    """
    Build and return a PostgreSQL DSN (Data Source Name).

    Best approach:
    - Use DATABASE_URL if it exists (common in Flask and cloud setups).

    Fallback approach:
    - Construct the DSN from individual Postgres environment variables.
      This makes the code more flexible and easier to debug if needed.
    """
    dsn = os.getenv("DATABASE_URL")
    if dsn:
        return dsn

    # Fallback to individual Postgres variables if DATABASE_URL is not set
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    user = os.getenv("PGUSER", "postgres")
    password = os.getenv("PGPASSWORD", "")
    dbname = os.getenv("PGDATABASE", "gradcafe")

    return (
        f"host={host} "
        f"port={port} "
        f"user={user} "
        f"password={password} "
        f"dbname={dbname}"
    )


@contextmanager
def get_conn():
    """
    Context manager that yields a PostgreSQL connection.

    Using a context manager ensures that the database connection is
    always closed properly, even if an error occurs during execution.
    """
    conn = psycopg2.connect(get_db_dsn())
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_cursor(dict_rows: bool = False):
    """
    Context manager that yields a database cursor.

    Parameters:
    - dict_rows (bool): If True, query results are returned as dictionaries
      instead of tuples, which can make code more readable.

    This function also handles commit and rollback automatically:
    - Commits if everything is succeeds
    - Rolls back if an exception comes up
    """
    with get_conn() as conn:
        cursor_factory = RealDictCursor if dict_rows else None
        cur = conn.cursor(cursor_factory=cursor_factory)

        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
