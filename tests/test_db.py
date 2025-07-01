import os
import pytest
from unittest.mock import patch, MagicMock, call
from web.db import _get_pool, get_conn, query, execute
import psycopg2
from psycopg2.extras import RealDictCursor


@pytest.fixture
def mock_pool():
    pool_mock = MagicMock()
    conn_mock = MagicMock()
    cursor_mock = MagicMock()
    conn_mock.cursor.return_value.__enter__.return_value = cursor_mock
    pool_mock.getconn.return_value = conn_mock
    return pool_mock, conn_mock, cursor_mock


def test_get_pool_initialization():
    with patch('web.db.pool.SimpleConnectionPool') as mock_pool_init:
        mock_pool_init.return_value = 'test_pool'
        with patch('web.db._POOL', None):  # Ensure _POOL is None
            # Test with default values
            result = _get_pool()
            assert result == 'test_pool'
            mock_pool_init.assert_called_once()
            _, kwargs = mock_pool_init.call_args
            assert kwargs['host'] == 'localhost'
            assert kwargs['port'] == 5464
            assert kwargs['dbname'] == 'ctgov-web'


def test_get_pool_default_pool_size():
    """Test that _get_pool uses default pool size of 5 when not specified."""
    with patch('web.db.pool.SimpleConnectionPool') as mock_pool_init, \
         patch.dict(os.environ, {}, clear=True), \
         patch('web.db._POOL', None):
        mock_pool_init.return_value = 'test_pool'
        
        result = _get_pool()
        assert result == 'test_pool'
        
        # Check that minconn=1 and maxconn=5 (default) were used
        args, _ = mock_pool_init.call_args
        assert args[0] == 1  # minconn
        assert args[1] == 5  # maxconn (default)


def test_get_pool_with_env_vars():
    with patch('web.db.pool.SimpleConnectionPool') as mock_pool_init, \
         patch.dict(os.environ, {
             'DB_HOST': 'test_host',
             'DB_PORT': '1234',
             'DB_NAME': 'test_db',
             'DB_USER': 'test_user',
             'DB_PASSWORD': 'test_pass',
             'DB_POOL_SIZE': '10'
         }):
        with patch('web.db._POOL', None):  # Ensure _POOL is None
            mock_pool_init.return_value = 'test_pool'
            result = _get_pool()
            assert result == 'test_pool'
            _, kwargs = mock_pool_init.call_args
            assert kwargs['host'] == 'test_host'
            assert kwargs['port'] == 1234
            assert kwargs['dbname'] == 'test_db'
            assert kwargs['user'] == 'test_user'
            assert kwargs['password'] == 'test_pass'


def test_get_pool_already_initialized():
    """Test that _get_pool returns existing pool if already initialized."""
    with patch('web.db._POOL', 'existing_pool'):
        result = _get_pool()
        assert result == 'existing_pool'


def test_get_pool_invalid_pool_size():
    """Test that _get_pool raises ValueError with invalid DB_POOL_SIZE."""
    with patch('web.db.pool.SimpleConnectionPool') as mock_pool_init, \
         patch.dict(os.environ, {'DB_POOL_SIZE': 'invalid'}), \
         patch('web.db._POOL', None):
        
        # The current implementation doesn't handle invalid values,
        # so we expect a ValueError
        with pytest.raises(ValueError, match="invalid literal for int()"):
            _get_pool()


def test_get_pool_initialization_error():
    """Test behavior when pool initialization fails."""
    with patch('web.db.pool.SimpleConnectionPool') as mock_pool_init, \
         patch('web.db._POOL', None):
        mock_pool_init.side_effect = psycopg2.OperationalError("could not connect to server")
        
        with pytest.raises(psycopg2.OperationalError):
            _get_pool()


def test_get_conn_context_manager(mock_pool):
    mock_pool_obj, conn_mock, _ = mock_pool
    
    with patch('web.db._get_pool', return_value=mock_pool_obj):
        with get_conn() as conn:
            assert conn == conn_mock
            mock_pool_obj.getconn.assert_called_once()
        
        # Verify connection is returned to pool after context exits
        mock_pool_obj.putconn.assert_called_once_with(conn_mock)


def test_get_conn_with_exception(mock_pool):
    """Test that connection is returned to pool even when exception occurs."""
    mock_pool_obj, conn_mock, _ = mock_pool
    
    with patch('web.db._get_pool', return_value=mock_pool_obj):
        try:
            with get_conn() as conn:
                assert conn == conn_mock
                mock_pool_obj.getconn.assert_called_once()
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Verify connection is still returned to pool after exception
        mock_pool_obj.putconn.assert_called_once_with(conn_mock)


def test_query_fetchall(mock_pool):
    mock_pool_obj, _, cursor_mock = mock_pool
    cursor_mock.fetchall.return_value = [{'id': 1}, {'id': 2}]
    
    with patch('web.db._get_pool', return_value=mock_pool_obj):
        result = query('SELECT * FROM test')
        assert result == [{'id': 1}, {'id': 2}]
        cursor_mock.execute.assert_called_with('SELECT * FROM test', [])
        cursor_mock.fetchall.assert_called_once()


def test_query_fetchone(mock_pool):
    mock_pool_obj, _, cursor_mock = mock_pool
    cursor_mock.fetchone.return_value = {'id': 1}
    
    with patch('web.db._get_pool', return_value=mock_pool_obj):
        result = query('SELECT * FROM test WHERE id=%s', [1], fetchone=True)
        assert result == {'id': 1}
        cursor_mock.execute.assert_called_with('SELECT * FROM test WHERE id=%s', [1])
        cursor_mock.fetchone.assert_called_once()


def test_query_with_none_params(mock_pool):
    """Test query with None params."""
    mock_pool_obj, _, cursor_mock = mock_pool
    cursor_mock.fetchall.return_value = [{'id': 1}, {'id': 2}]
    
    with patch('web.db._get_pool', return_value=mock_pool_obj):
        result = query('SELECT * FROM test', None)
        assert result == [{'id': 1}, {'id': 2}]
        cursor_mock.execute.assert_called_with('SELECT * FROM test', [])
        cursor_mock.fetchall.assert_called_once()


def test_query_empty_result(mock_pool):
    """Test query when no results are returned."""
    mock_pool_obj, _, cursor_mock = mock_pool
    cursor_mock.fetchall.return_value = []
    cursor_mock.fetchone.return_value = None
    
    with patch('web.db._get_pool', return_value=mock_pool_obj):
        # Test fetchall with empty result
        result = query('SELECT * FROM test WHERE id=999')
        assert result == []
        
        # Test fetchone with empty result
        result = query('SELECT * FROM test WHERE id=999', fetchone=True)
        assert result is None


def test_query_with_db_error(mock_pool):
    """Test query when database error occurs."""
    mock_pool_obj, _, cursor_mock = mock_pool
    cursor_mock.execute.side_effect = psycopg2.Error("Database error")
    
    with patch('web.db._get_pool', return_value=mock_pool_obj):
        with pytest.raises(psycopg2.Error):
            query('SELECT * FROM test')


def test_query_uses_real_dict_cursor(mock_pool):
    """Test that query uses RealDictCursor."""
    mock_pool_obj, conn_mock, _ = mock_pool
    
    with patch('web.db._get_pool', return_value=mock_pool_obj):
        query('SELECT * FROM test')
        conn_mock.cursor.assert_called_with(cursor_factory=RealDictCursor)


def test_query_sql_injection_protection(mock_pool):
    """Test that parameterized queries protect against SQL injection."""
    mock_pool_obj, _, cursor_mock = mock_pool
    malicious_input = "1; DROP TABLE users;"
    
    with patch('web.db._get_pool', return_value=mock_pool_obj):
        query('SELECT * FROM test WHERE id=%s', [malicious_input])
        
        # The SQL and parameters should be passed separately to execute
        # and not interpolated into the SQL string
        cursor_mock.execute.assert_called_with(
            'SELECT * FROM test WHERE id=%s', 
            [malicious_input]
        )


def test_execute(mock_pool):
    mock_pool_obj, conn_mock, cursor_mock = mock_pool
    
    with patch('web.db._get_pool', return_value=mock_pool_obj):
        execute('INSERT INTO test VALUES (%s)', [1])
        cursor_mock.execute.assert_called_with('INSERT INTO test VALUES (%s)', [1])
        conn_mock.commit.assert_called_once()


def test_execute_with_none_params(mock_pool):
    """Test execute with None params."""
    mock_pool_obj, conn_mock, cursor_mock = mock_pool
    
    with patch('web.db._get_pool', return_value=mock_pool_obj):
        execute('INSERT INTO test VALUES (DEFAULT)', None)
        cursor_mock.execute.assert_called_with('INSERT INTO test VALUES (DEFAULT)', [])
        conn_mock.commit.assert_called_once()


def test_execute_with_db_error(mock_pool):
    """Test execute when database error occurs."""
    mock_pool_obj, conn_mock, cursor_mock = mock_pool
    cursor_mock.execute.side_effect = psycopg2.Error("Database error")
    
    with patch('web.db._get_pool', return_value=mock_pool_obj):
        with pytest.raises(psycopg2.Error):
            execute('INSERT INTO test VALUES (%s)', [1])
        
        # Verify commit was not called after error
        conn_mock.commit.assert_not_called()


def test_execute_sql_injection_protection(mock_pool):
    """Test that parameterized queries in execute protect against SQL injection."""
    mock_pool_obj, conn_mock, cursor_mock = mock_pool
    malicious_input = "value'); DROP TABLE users; --"
    
    with patch('web.db._get_pool', return_value=mock_pool_obj):
        execute('INSERT INTO test VALUES (%s)', [malicious_input])
        
        # The SQL and parameters should be passed separately to execute
        # and not interpolated into the SQL string
        cursor_mock.execute.assert_called_with(
            'INSERT INTO test VALUES (%s)', 
            [malicious_input]
        )
        conn_mock.commit.assert_called_once()


def test_nested_transactions(mock_pool):
    """Test nested transactions behavior."""
    mock_pool_obj, conn_mock, cursor_mock = mock_pool
    
    with patch('web.db._get_pool', return_value=mock_pool_obj):
        # First transaction
        execute('INSERT INTO test VALUES (1)')
        
        # Second transaction
        execute('INSERT INTO test VALUES (2)')
        
        # Both should commit independently
        assert conn_mock.commit.call_count == 2
        cursor_mock.execute.assert_has_calls([
            call('INSERT INTO test VALUES (1)', []),
            call('INSERT INTO test VALUES (2)', [])
        ])


def test_pool_getconn_error():
    """Test handling when pool.getconn raises an exception."""
    mock_pool = MagicMock()
    mock_pool.getconn.side_effect = psycopg2.pool.PoolError("Connection pool exhausted")
    
    with patch('web.db._get_pool', return_value=mock_pool):
        with pytest.raises(psycopg2.pool.PoolError):
            with get_conn():
                pass  # This should not be executed


def test_pool_putconn_error(mock_pool):
    """Test that exceptions in putconn are propagated."""
    mock_pool_obj, conn_mock, _ = mock_pool
    mock_pool_obj.putconn.side_effect = Exception("Error returning connection to pool")
    
    with patch('web.db._get_pool', return_value=mock_pool_obj):
        # The current implementation doesn't catch exceptions in putconn
        with pytest.raises(Exception, match="Error returning connection to pool"):
            with get_conn() as conn:
                assert conn == conn_mock


def test_execute_uses_standard_cursor(mock_pool):
    """Test that execute uses standard cursor (not RealDictCursor)."""
    mock_pool_obj, conn_mock, _ = mock_pool
    
    with patch('web.db._get_pool', return_value=mock_pool_obj):
        execute('INSERT INTO test VALUES (1)')
        # Should not pass cursor_factory parameter
        conn_mock.cursor.assert_called_with()


def test_connection_closed_during_query(mock_pool):
    """Test behavior when connection is closed during query execution."""
    mock_pool_obj, conn_mock, cursor_mock = mock_pool
    cursor_mock.execute.side_effect = psycopg2.OperationalError("connection already closed")
    
    with patch('web.db._get_pool', return_value=mock_pool_obj):
        with pytest.raises(psycopg2.OperationalError):
            query('SELECT * FROM test')