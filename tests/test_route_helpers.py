import pytest
from unittest.mock import patch, MagicMock
from web.utils.route_helpers import (
    compliance_counts, 
    process_index_request, 
    process_search_request, 
    process_reporting_request,
    parse_request_arg
)
from datetime import date


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
    
    @patch('web.utils.queries.QueryManager.get_compliance_rate')
    @patch('web.utils.route_helpers.compliance_counts')
    @patch('web.utils.route_helpers.paginate')
    @patch('web.utils.queries.QueryManager.get_all_trials')
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
    
    @patch('web.utils.queries.QueryManager.search_trials')
    @patch('web.utils.queries.QueryManager.get_compliance_rate')
    @patch('web.utils.route_helpers.paginate')
    @patch('web.utils.route_helpers.compliance_counts')
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

    @patch('web.utils.queries.QueryManager.search_trials')
    @patch('web.utils.queries.QueryManager.get_compliance_rate')
    @patch('web.utils.route_helpers.paginate')
    @patch('web.utils.route_helpers.compliance_counts')
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


class TestProcessReportingRequest:
    """Tests for reporting helper."""

    def test_reporting_request_with_range(self):
        mock_qm = MagicMock()
        mock_qm.get_compliance_status_time_series.return_value = [
            {'start_date': date(2024, 1, 1), 'compliance_status': 'Compliant', 'status_count': 2},
            {'start_date': '2024-01-02', 'compliance_status': 'Incompliant', 'status_count': 1},
            {'start_date': '2024-01-02', 'compliance_status': 'Compliant', 'status_count': 3},
        ]

        result = process_reporting_request('2024-01-01', '2024-01-03', QueryManager=mock_qm)

        mock_qm.get_compliance_status_time_series.assert_called_once_with(
            start_date='2024-01-01',
            end_date='2024-01-03'
        )
        assert result['template'] == 'reporting.html'
        assert result['start_date'] == '2024-01-01'
        assert result['end_date'] == '2024-01-03'
        assert len(result['time_series']) == 3
        first_day = result['time_series'][0]
        assert first_day['date'] == '2024-01-01'
        assert first_day['compliant'] == 2
        assert first_day['incompliant'] == 0
        second_day = result['time_series'][1]
        assert second_day['date'] == '2024-01-02'
        assert second_day['incompliant'] == 1
        assert second_day['compliant'] == 3

    @patch('web.utils.route_helpers.date')
    def test_reporting_request_defaults(self, mock_date_cls):
        mock_date_cls.today.return_value = date(2024, 4, 30)
        mock_qm = MagicMock()
        mock_qm.get_compliance_status_time_series.return_value = []

        result = process_reporting_request(QueryManager=mock_qm)

        assert result['end_date'] == '2024-04-30'
        assert result['start_date'] == '2024-04-01'
        mock_qm.get_compliance_status_time_series.assert_called_once_with(
            start_date='2024-04-01',
            end_date='2024-04-30'
        )

    def test_reporting_request_swaps_dates(self):
        mock_qm = MagicMock()
        mock_qm.get_compliance_status_time_series.return_value = []

        result = process_reporting_request('2024-03-10', '2024-03-01', QueryManager=mock_qm)

        assert result['start_date'] == '2024-03-01'
        assert result['end_date'] == '2024-03-10'
        mock_qm.get_compliance_status_time_series.assert_called_once_with(
            start_date='2024-03-01',
            end_date='2024-03-10'
        )
