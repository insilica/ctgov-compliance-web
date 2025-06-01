import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
from contextlib import contextmanager


_POOL = None


def _get_pool():
    global _POOL
    if _POOL is None:
        _POOL = pool.SimpleConnectionPool(
            1,
            int(os.environ.get('DB_POOL_SIZE', 5)),
            host=os.environ.get('DB_HOST', 'localhost'),
            port=os.environ.get('DB_PORT', '5464'),
            dbname=os.environ.get('DB_NAME', 'ctgov-web'),
            user=os.environ.get('DB_USER', 'postgres'),
            password=os.environ.get('DB_PASSWORD', 'devpassword'),
        )
    return _POOL


@contextmanager
def get_conn():
    conn = _get_pool().getconn()
    try:
        yield conn
    finally:
        _get_pool().putconn(conn)


def query(sql, params=None, fetchone=False):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params or [])
            data = cur.fetchone() if fetchone else cur.fetchall()
    return data


def execute(sql, params=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or [])
            conn.commit()
