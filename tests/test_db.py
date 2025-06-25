import os
import pytest
from unittest.mock import patch, MagicMock
from web.db import _get_pool, get_conn, query, execute


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
            assert kwargs['port'] == '5464'
            assert kwargs['dbname'] == 'ctgov-web'


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
            assert kwargs['port'] == '1234'
            assert kwargs['dbname'] == 'test_db'
            assert kwargs['user'] == 'test_user'
            assert kwargs['password'] == 'test_pass'


def test_get_conn_context_manager(mock_pool):
    mock_pool_obj, conn_mock, _ = mock_pool
    
    with patch('web.db._get_pool', return_value=mock_pool_obj):
        with get_conn() as conn:
            assert conn == conn_mock
            mock_pool_obj.getconn.assert_called_once()
        
        # Verify connection is returned to pool after context exits
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


def test_execute(mock_pool):
    mock_pool_obj, conn_mock, cursor_mock = mock_pool
    
    with patch('web.db._get_pool', return_value=mock_pool_obj):
        execute('INSERT INTO test VALUES (%s)', [1])
        cursor_mock.execute.assert_called_with('INSERT INTO test VALUES (%s)', [1])
        conn_mock.commit.assert_called_once()