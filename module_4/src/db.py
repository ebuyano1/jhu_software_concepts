"""
db.py - Database Connection Manager
"""
import os
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

def get_db_dsn(env_overrides=None) -> str:
    """
    Build and return a PostgreSQL DSN (Data Source Name).
    Allows overrides for testing purposes.
    """
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)

    dsn = env.get("DATABASE_URL")
    if dsn:
        return dsn

    host = env.get("PGHOST", "localhost")
    port = env.get("PGPORT", "5432")
    user = env.get("PGUSER", "postgres")
    password = env.get("PGPASSWORD", "")
    dbname = env.get("PGDATABASE", "gradcafe")

    return (
        f"host={host} "
        f"port={port} "
        f"user={user} "
        f"password={password} "
        f"dbname={dbname}"
    )

@contextmanager
def get_conn(dsn=None):
    """
    Context manager that yields a PostgreSQL connection.
    Accepts an explicit DSN for testing.
    """
    if dsn is None:
        dsn = get_db_dsn()
        
    conn = psycopg2.connect(dsn)
    try:
        yield conn
    finally:
        conn.close()

@contextmanager
def get_cursor(dict_rows: bool = False, dsn=None):
    """
    Context manager that yields a database cursor.
    """
    with get_conn(dsn=dsn) as conn:
        cursor_factory = RealDictCursor if dict_rows else None
        cur = conn.cursor(cursor_factory=cursor_factory)
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise