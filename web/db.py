import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
from contextlib import contextmanager
from opentelemetry import trace

tracer = trace.get_tracer(__name__)


_POOL = None


def _get_pool():
    global _POOL
    if _POOL is None:
        # Check if we're connecting to Cloud SQL
        db_host = os.environ.get('DB_HOST', 'localhost')
        
        # Cloud SQL connection configuration
        if db_host.startswith('/cloudsql/'):
            # Unix socket connection for Cloud SQL
            connection_kwargs = {
                'host': db_host,
                'dbname': os.environ.get('DB_NAME', 'ctgov-web'),
                'user': os.environ.get('DB_USER', 'postgres'),
                'password': os.environ.get('DB_PASSWORD', 'devpassword'),
            }
        else:
            # TCP connection for local or other remote databases
            connection_kwargs = {
                'host': db_host,
                'port': os.environ.get('DB_PORT', '5464'),
                'dbname': os.environ.get('DB_NAME', 'ctgov-web'),
                'user': os.environ.get('DB_USER', 'postgres'),
                'password': os.environ.get('DB_PASSWORD', 'devpassword'),
            }
        
        # Handle DB_POOL_SIZE safely - it must be an integer for SimpleConnectionPool
        try:
            pool_size = int(os.environ.get('DB_POOL_SIZE', '5'))
        except (ValueError, TypeError):
            pool_size = 5  # Default fallback
        
        with tracer.start_as_current_span("db.init_pool") as span:
            span.set_attribute("db.pool.size", pool_size)
            span.set_attribute("db.host", connection_kwargs.get('host', ''))
            _POOL = pool.SimpleConnectionPool(
                1,
                pool_size,
                **connection_kwargs
            )
    return _POOL


@contextmanager
def get_conn():
    with tracer.start_as_current_span("db.get_conn"):
        conn = _get_pool().getconn()
        try:
            yield conn
        finally:
            _get_pool().putconn(conn)


def query(sql, params=None, fetchone=False):
    with tracer.start_as_current_span("db.query") as span:
        span.set_attribute("db.query.fetchone", bool(fetchone))
        # Avoid recording full SQL/params to reduce PII; include lengths only
        span.set_attribute("db.query.sql_length", len(sql) if isinstance(sql, str) else 0)
        span.set_attribute("db.query.params_count", len(params) if isinstance(params, (list, tuple)) else (1 if params is not None else 0))
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params or [])
                data = cur.fetchone() if fetchone else cur.fetchall()
    return data


def execute(sql, params=None):
    with tracer.start_as_current_span("db.execute") as span:
        span.set_attribute("db.execute.sql_length", len(sql) if isinstance(sql, str) else 0)
        span.set_attribute("db.execute.params_count", len(params) if isinstance(params, (list, tuple)) else (1 if params is not None else 0))
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or [])
                conn.commit()


def check_data_population():
    """Check if the database has been populated with data."""
    try:
        result = query("SELECT COUNT(*) as count FROM organization", fetchone=True)
        return result['count'] > 0 if result else False
    except Exception:
        return False


def mark_data_populated():
    """Mark that the database has been populated by creating a flag table."""
    try:
        execute("""
            CREATE TABLE IF NOT EXISTS data_population_flag (
                id SERIAL PRIMARY KEY,
                populated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                version VARCHAR(50) DEFAULT '1.0'
            )
        """)
        
        # Only insert if not already marked
        existing = query("SELECT COUNT(*) as count FROM data_population_flag", fetchone=True)
        if existing['count'] == 0:
            execute("INSERT INTO data_population_flag (version) VALUES ('1.0')")
            return True
        return False
    except Exception as e:
        print(f"Error marking data as populated: {e}")
        return False


def is_data_populated():
    """Check if data has been populated based on flag table."""
    try:
        result = query("SELECT COUNT(*) as count FROM data_population_flag", fetchone=True)
        return result['count'] > 0 if result else False
    except Exception:
        return False
