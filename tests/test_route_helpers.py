import pytest
from unittest.mock import patch, MagicMock
from web.backend.services.route_helpers import (
    compliance_counts, 
    process_index_request, 
    process_search_request, 
    parse_request_arg
)


class TestComplianceCounts:
    """Test the compliance_counts function."""
    
    def test_compliance_counts_with_data(self):
        """Test compliance_counts function with trial data."""
        rates = [{'compliant_count': 10, 'incompliant_count': 5}]
        on_time, late = compliance_counts(rates)
        assert on_time == 10
        assert late == 5

    def test_compliance_counts_empty_trials(self):
        """Test compliance_counts function with empty trials data."""
        rates = [{'compliant_count': 0, 'incompliant_count': 0}]
        on_time, late = compliance_counts(rates)
        assert on_time == 0
        assert late == 0


class TestProcessIndexRequest:
    """Test the process_index_request function."""
    
    @patch('web.backend.repositories.queries.QueryManager.get_compliance_rate')
    @patch('web.backend.services.route_helpers.compliance_counts')
    @patch('web.backend.services.route_helpers.paginate')
    @patch('web.backend.repositories.queries.QueryManager.get_all_trials')
    def test_process_index_request(self, mock_get_all_trials, mock_paginate, mock_compliance_counts, mock_get_compliance_rate):
        """Test processing index request."""
        # Setup mocks
        trials = [{'nct_id': 'NCT001', 'status': 'Compliant'}]
        mock_get_all_trials.side_effect = [trials, [{'count': 50}]]
        
        mock_pagination = MagicMock()
        mock_pagination.items_page = trials
        mock_paginate.return_value = (mock_pagination, 10)
        
        mock_get_compliance_rate.return_value = [{'compliant_count': 30, 'incompliant_count': 20}]
        mock_compliance_counts.return_value = (30, 20)
        
        # Call function with explicit pagination parameters
        result = process_index_request(page=1, per_page=10)
        
        # Verify result
        expected = {
            'template': 'dashboards/home.html',
            'trials': trials,
            'pagination': mock_pagination,
            'per_page': 10,
            'on_time_count': 30,
            'late_count': 20
        }
        assert result == expected


class TestProcessSearchRequest:
    """Test the process_search_request function."""
    
    @patch('web.backend.repositories.queries.QueryManager.search_trials')
    @patch('web.backend.repositories.queries.QueryManager.get_compliance_rate')
    @patch('web.backend.services.route_helpers.paginate')
    @patch('web.backend.services.route_helpers.compliance_counts')
    def test_process_search_request_with_params(self, mock_compliance_counts, mock_paginate, mock_get_compliance_rate, mock_search_trials):
        """Test processing search request with search parameters."""
        search_params = {'title': 'cancer', 'nct_id': None}
        compliance_status_list = []
        
        search_results = [{'nct_id': 'NCT001', 'status': 'Compliant'}]
        count_results = [{'count': 25}]

        def mock_search_trials_side_effect(*args, **kwargs):
            if kwargs.get('count'):
                return count_results
            return search_results

        mock_search_trials.side_effect = mock_search_trials_side_effect
        mock_get_compliance_rate.return_value = [{'compliant_count': 1, 'incompliant_count': 0}]

        mock_pagination = MagicMock()
        mock_pagination.items_page = search_results
        mock_paginate.return_value = (mock_pagination, 10)
        
        mock_compliance_counts.return_value = (1, 0)
        
        # Call function with explicit pagination parameters
        result = process_search_request(search_params, compliance_status_list, page=1, per_page=10)
        
        # Verify result
        expected = {
            'template': 'dashboards/home.html',
            'trials': search_results,
            'pagination': mock_pagination,
            'per_page': 10,
            'on_time_count': 1,
            'late_count': 0,
            'is_search': True
        }
        assert result == expected

    @patch('web.backend.repositories.queries.QueryManager.search_trials')
    @patch('web.backend.repositories.queries.QueryManager.get_compliance_rate')
    @patch('web.backend.services.route_helpers.paginate')
    @patch('web.backend.services.route_helpers.compliance_counts')
    def test_process_search_request_with_compliance_status(self, mock_compliance_counts, mock_paginate, mock_get_compliance_rate, mock_search_trials):
        """Test processing search request with compliance status only."""
        search_params = {'title': None, 'nct_id': None}
        compliance_status_list = ['Compliant']

        search_results = [{'nct_id': 'NCT001', 'status': 'Compliant'}]
        count_results = [{'count': 25}]

        def mock_search_trials_side_effect(*args, **kwargs):
            if kwargs.get('count'):
                return count_results
            return search_results

        mock_search_trials.side_effect = mock_search_trials_side_effect

        mock_get_compliance_rate.return_value = [{'compliant_count': 1, 'incompliant_count': 0}]

        mock_pagination = MagicMock()
        mock_pagination.items_page = search_results
        mock_paginate.return_value = (mock_pagination, 10)
        
        mock_compliance_counts.return_value = (1, 0)
        
        # Call function with explicit pagination parameters
        result = process_search_request(search_params, compliance_status_list, page=1, per_page=10)
        
        # Verify result
        expected = {
            'template': 'dashboards/home.html',
            'trials': search_results,
            'pagination': mock_pagination,
            'per_page': 10,
            'on_time_count': 1,
            'late_count': 0,
            'is_search': True
        }
        assert result == expected

        # Verify mocks were called correctly
        assert mock_search_trials.call_count == 2
        mock_search_trials.assert_any_call(search_params, page=1, per_page=10)
        mock_search_trials.assert_any_call(search_params, count="COUNT(trial_id)")
        mock_paginate.assert_called_once_with(search_results, total_entries=25)
        # Note: compliance_counts is called with QueryManager.get_compliance_rate() result, not search_results
        mock_compliance_counts.assert_called_once()

    def test_process_search_request_no_params(self):
        """Test processing search request with no parameters."""
        search_params = {'title': None, 'nct_id': None}
        compliance_status_list = []
        
        # Call function
        result = process_search_request(search_params, compliance_status_list, page=1, per_page=10)
        
        # Should return basic template without search results
        expected = {
            'template': 'dashboards/home.html'
        }
        assert result == expected


class TestParseRequestArg:
    """Test the parse_request_arg function."""
    
    def test_parse_request_arg_valid_digits(self):
        """Test parse_request_arg with valid digit strings."""
        assert parse_request_arg('123') == 123
        assert parse_request_arg('0') == 0
        assert parse_request_arg('999') == 999

    def test_parse_request_arg_invalid_values(self):
        """Test parse_request_arg with invalid values."""
        assert parse_request_arg('abc') is None
        assert parse_request_arg('') is None
        assert parse_request_arg(None) is None
        assert parse_request_arg('12.5') is None  # float as string
        assert parse_request_arg('-5') is None  # negative number


class TestEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_search_request_edge_cases(self):
        """Test search request with various edge case inputs."""
        # Test with all None parameters
        search_params = {'title': None, 'nct_id': None}
        compliance_status_list = None
        
        result = process_search_request(search_params, compliance_status_list, page=1, per_page=10)
        
        # Should return basic template
        expected = {
            'template': 'dashboards/home.html'
        }
        assert result == expected 