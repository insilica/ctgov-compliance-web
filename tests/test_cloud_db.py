"""
Tests for cloud database functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from web.db import (
    _get_pool, 
    check_data_population, 
    mark_data_populated, 
    is_data_populated
)


class TestCloudDBConnection:
    """Test cloud database connection handling."""

    @patch.dict('os.environ', {'DB_HOST': '/cloudsql/project:region:instance'})
    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_cloud_sql_unix_socket_connection(self, mock_pool):
        """Test that Cloud SQL unix socket connections are handled correctly."""
        # Reset the global pool
        import web.db
        web.db._POOL = None
        
        # Call the function
        _get_pool()
        
        # Verify the pool was created with correct parameters
        mock_pool.assert_called_once()
        call_args = mock_pool.call_args[1]  # keyword arguments
        
        assert call_args['host'] == '/cloudsql/project:region:instance'
        assert 'port' not in call_args  # Port should not be set for unix socket
        assert call_args['dbname'] == 'ctgov-web'
        assert call_args['user'] == 'postgres'

    @patch.dict('os.environ', {'DB_HOST': 'localhost', 'DB_PORT': '5432'})
    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_tcp_connection(self, mock_pool):
        """Test that TCP connections are handled correctly."""
        # Reset the global pool
        import web.db
        web.db._POOL = None
        
        # Call the function
        _get_pool()
        
        # Verify the pool was created with correct parameters
        mock_pool.assert_called_once()
        call_args = mock_pool.call_args[1]  # keyword arguments
        
        assert call_args['host'] == 'localhost'
        assert call_args['port'] == 5432
        assert call_args['dbname'] == 'ctgov-web'
        assert call_args['user'] == 'postgres'


class TestDataPopulationTracking:
    """Test data population tracking functionality."""

    @patch('web.db.query')
    def test_check_data_population_with_data(self, mock_query):
        """Test checking data population when data exists."""
        mock_query.return_value = {'count': 5}
        
        result = check_data_population()
        
        assert result is True
        mock_query.assert_called_once_with("SELECT COUNT(*) as count FROM organization", fetchone=True)

    @patch('web.db.query')
    def test_check_data_population_without_data(self, mock_query):
        """Test checking data population when no data exists."""
        mock_query.return_value = {'count': 0}
        
        result = check_data_population()
        
        assert result is False

    @patch('web.db.query')
    def test_check_data_population_error(self, mock_query):
        """Test checking data population when query fails."""
        mock_query.side_effect = Exception("Database error")
        
        result = check_data_population()
        
        assert result is False

    @patch('web.db.execute')
    @patch('web.db.query')
    def test_mark_data_populated_success(self, mock_query, mock_execute):
        """Test marking data as populated successfully."""
        # Mock that no flag exists yet
        mock_query.return_value = {'count': 0}
        
        result = mark_data_populated()
        
        assert result is True
        # Should create table and insert flag
        assert mock_execute.call_count == 2

    @patch('web.db.execute')
    @patch('web.db.query')
    def test_mark_data_populated_already_marked(self, mock_query, mock_execute):
        """Test marking data as populated when already marked."""
        # Mock that flag already exists
        mock_query.return_value = {'count': 1}
        
        result = mark_data_populated()
        
        assert result is False
        # Should only create table, not insert
        assert mock_execute.call_count == 1

    @patch('web.db.query')
    def test_is_data_populated_true(self, mock_query):
        """Test checking if data is populated when flag exists."""
        mock_query.return_value = {'count': 1}
        
        result = is_data_populated()
        
        assert result is True

    @patch('web.db.query')
    def test_is_data_populated_false(self, mock_query):
        """Test checking if data is populated when flag doesn't exist."""
        mock_query.return_value = {'count': 0}
        
        result = is_data_populated()
        
        assert result is False

    @patch('web.db.query')
    def test_is_data_populated_error(self, mock_query):
        """Test checking if data is populated when query fails."""
        mock_query.side_effect = Exception("Database error")
        
        result = is_data_populated()
        
        assert result is False 