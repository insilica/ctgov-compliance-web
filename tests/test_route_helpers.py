"""
Tests for the web/utils/route_helpers.py module.

These tests directly test the helper functions extracted from routes.py,
providing much better line coverage while avoiding Flask context issues.
"""

import pytest
from unittest.mock import patch, MagicMock
from web.utils.route_helpers import (
    compliance_counts,
    process_index_request,
    process_search_request,
    process_organization_dashboard_request,
    process_compare_organizations_request,
    process_user_dashboard_request,
    parse_request_arg
)


class TestComplianceCounts:
    """Test the compliance_counts function."""
    
    @patch('builtins.__import__')
    def test_compliance_counts_with_data(self, mock_import):
        """Test compliance_counts with trial data."""
        # Mock pandas import
        mock_pd = MagicMock()
        def side_effect(name, *args, **kwargs):
            if name == 'pandas':
                return mock_pd
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = side_effect
        
        # Mock DataFrame and value_counts
        mock_df = MagicMock()
        mock_pd.DataFrame.return_value = mock_df
        mock_df.empty = False
        
        mock_value_counts = MagicMock()
        mock_df.__getitem__.return_value.value_counts.return_value = mock_value_counts
        mock_value_counts.get.side_effect = lambda x, default=0: {'Compliant': 5, 'Incompliant': 3}.get(x, default)
        
        # Test data
        trials = [
            {'nct_id': 'NCT001', 'status': 'Compliant'},
            {'nct_id': 'NCT002', 'status': 'Incompliant'},
            {'nct_id': 'NCT003', 'status': 'Compliant'}
        ]
        
        result = compliance_counts(trials)
        
        assert result == (5, 3)
        mock_pd.DataFrame.assert_called_once_with(trials)
        mock_df.__getitem__.assert_called_once_with('status')
    
    @patch('builtins.__import__')
    def test_compliance_counts_empty_trials(self, mock_import):
        """Test compliance_counts with empty trials list."""
        # Mock pandas import
        mock_pd = MagicMock()
        def side_effect(name, *args, **kwargs):
            if name == 'pandas':
                return mock_pd
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = side_effect
        
        # Mock DataFrame
        mock_df = MagicMock()
        mock_pd.DataFrame.return_value = mock_df
        mock_df.empty = True
        
        # Mock empty Series
        mock_series = MagicMock()
        mock_pd.Series.return_value = mock_series
        mock_series.get.return_value = 0
        
        result = compliance_counts([])
        
        assert result == (0, 0)
        mock_pd.DataFrame.assert_called_once_with([])


class TestProcessIndexRequest:
    """Test the process_index_request function."""
    
    @patch('web.utils.route_helpers.compliance_counts')
    @patch('web.utils.route_helpers.paginate')
    @patch('web.utils.route_helpers.get_all_trials_count')
    @patch('web.utils.route_helpers.get_all_trials')
    def test_process_index_request(self, mock_get_all_trials, mock_get_all_trials_count, mock_paginate, mock_compliance_counts):
        """Test processing index request."""
        # Setup mocks
        sample_trials = [{'nct_id': 'NCT001', 'status': 'Compliant'}]
        mock_get_all_trials.side_effect = [sample_trials, sample_trials]  # Called twice: once for paginated, once for all
        mock_get_all_trials_count.return_value = 100
        
        mock_pagination = MagicMock()
        mock_pagination.items_page = sample_trials
        mock_paginate.return_value = (mock_pagination, 10)
        
        mock_compliance_counts.return_value = (5, 3)
        
        # Call function with explicit pagination parameters
        result = process_index_request(page=1, per_page=10)
        
        # Verify result
        expected = {
            'template': 'dashboards/home.html',
            'trials': sample_trials,
            'pagination': mock_pagination,
            'per_page': 10,
            'on_time_count': 5,
            'late_count': 3
        }
        assert result == expected
        
        # Verify mocks were called correctly
        assert mock_get_all_trials.call_count == 2
        # First call with pagination parameters
        mock_get_all_trials.assert_any_call(page=1, per_page=10)
        # Second call without pagination parameters (for compliance counts)
        mock_get_all_trials.assert_any_call()
        mock_get_all_trials_count.assert_called_once()
        mock_paginate.assert_called_once_with(sample_trials, total_entries=100)
        mock_compliance_counts.assert_called_once_with(sample_trials)


class TestProcessSearchRequest:
    """Test the process_search_request function."""
    
    @patch('web.utils.route_helpers.compliance_counts')
    @patch('web.utils.route_helpers.paginate')
    @patch('web.utils.route_helpers.search_trials_count')
    @patch('web.utils.route_helpers.search_trials')
    def test_process_search_request_with_params(self, mock_search_trials, mock_search_trials_count, mock_paginate, mock_compliance_counts):
        """Test processing search request with parameters."""
        # Setup mocks
        search_params = {'title': 'Cancer', 'nct_id': None}
        compliance_status_list = []
        
        search_results = [{'nct_id': 'NCT001', 'status': 'Compliant'}]
        mock_search_trials.side_effect = [search_results, search_results]  # Called twice
        mock_search_trials_count.return_value = 50
        
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
        mock_search_trials.assert_any_call(search_params)
        mock_search_trials_count.assert_called_once_with(search_params)
        mock_paginate.assert_called_once_with(search_results, total_entries=50)
        mock_compliance_counts.assert_called_once_with(search_results)

    def test_process_search_request_with_compliance_status(self):
        """Test processing search request with compliance status only."""
        search_params = {'title': None, 'nct_id': None}
        compliance_status_list = ['Compliant']
        
        with patch('web.utils.route_helpers.search_trials') as mock_search_trials, \
             patch('web.utils.route_helpers.search_trials_count') as mock_search_trials_count, \
             patch('web.utils.route_helpers.paginate') as mock_paginate, \
             patch('web.utils.route_helpers.compliance_counts') as mock_compliance_counts:
            
            search_results = [{'nct_id': 'NCT001', 'status': 'Compliant'}]
            mock_search_trials.side_effect = [search_results, search_results]
            mock_search_trials_count.return_value = 25
            
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
            mock_search_trials_count.assert_called_once_with(search_params)
            mock_paginate.assert_called_once_with(search_results, total_entries=25)
            mock_compliance_counts.assert_called_once_with(search_results)

    def test_process_search_request_no_params(self):
        """Test processing search request with no parameters."""
        search_params = {'title': None, 'nct_id': None}
        compliance_status_list = []
        
        # Call function
        result = process_search_request(search_params, compliance_status_list, page=1, per_page=10)
        
        # Verify result
        expected = {
            'template': 'dashboards/home.html'
        }
        assert result == expected


class TestProcessOrganizationDashboardRequest:
    """Test the process_organization_dashboard_request function."""
    
    @patch('web.utils.route_helpers.compliance_counts')
    @patch('web.utils.route_helpers.paginate')
    @patch('web.utils.route_helpers.get_org_trials_count')
    @patch('web.utils.route_helpers.get_org_trials')
    def test_process_organization_dashboard_request(self, mock_get_org_trials, mock_get_org_trials_count, mock_paginate, mock_compliance_counts):
        """Test processing organization dashboard request."""
        # Setup mocks
        org_ids = '1%2C2%2C3'  # URL encoded "1,2,3"
        
        org_trials = [{'nct_id': 'NCT001', 'status': 'Compliant'}]
        mock_get_org_trials.side_effect = [org_trials, org_trials]
        mock_get_org_trials_count.return_value = 75
        
        mock_pagination = MagicMock()
        mock_pagination.items_page = org_trials
        mock_paginate.return_value = (mock_pagination, 10)
        
        mock_compliance_counts.return_value = (1, 0)
        
        # Call function with explicit pagination parameters
        result = process_organization_dashboard_request(org_ids, page=1, per_page=10)
        
        # Verify result
        expected = {
            'template': 'dashboards/organization.html',
            'trials': org_trials,
            'pagination': mock_pagination,
            'per_page': 10,
            'org_ids': '1,2,3',
            'on_time_count': 1,
            'late_count': 0
        }
        assert result == expected
        
        # Verify mocks were called correctly
        assert mock_get_org_trials.call_count == 2
        mock_get_org_trials.assert_any_call((1, 2, 3), page=1, per_page=10)
        mock_get_org_trials.assert_any_call((1, 2, 3))
        mock_get_org_trials_count.assert_called_once_with((1, 2, 3))
        mock_paginate.assert_called_once_with(org_trials, total_entries=75)
        mock_compliance_counts.assert_called_once_with(org_trials)

    @patch('web.utils.route_helpers.compliance_counts')
    @patch('web.utils.route_helpers.paginate')
    @patch('web.utils.route_helpers.get_org_trials_count')
    @patch('web.utils.route_helpers.get_org_trials')
    def test_process_organization_dashboard_request_empty_org_ids(self, mock_get_org_trials, mock_get_org_trials_count, mock_paginate, mock_compliance_counts):
        """Test processing organization dashboard request with empty org_ids."""
        # Setup mocks
        org_ids = ''
        
        org_trials = []
        mock_get_org_trials.side_effect = [org_trials, org_trials]
        mock_get_org_trials_count.return_value = 0
        
        mock_pagination = MagicMock()
        mock_pagination.items_page = []
        mock_paginate.return_value = (mock_pagination, 10)
        
        mock_compliance_counts.return_value = (0, 0)
        
        # Call function with explicit pagination parameters
        result = process_organization_dashboard_request(org_ids, page=1, per_page=10)
        
        # Verify result
        expected = {
            'template': 'dashboards/organization.html',
            'trials': [],
            'pagination': mock_pagination,
            'per_page': 10,
            'org_ids': '',
            'on_time_count': 0,
            'late_count': 0
        }
        assert result == expected
        
        # Verify mocks were called correctly
        assert mock_get_org_trials.call_count == 2
        mock_get_org_trials.assert_any_call((), page=1, per_page=10)
        mock_get_org_trials.assert_any_call(())
        mock_get_org_trials_count.assert_called_once_with(())
        mock_paginate.assert_called_once_with([], total_entries=0)
        mock_compliance_counts.assert_called_once_with([])

    @patch('web.utils.route_helpers.compliance_counts')
    @patch('web.utils.route_helpers.paginate')
    @patch('web.utils.route_helpers.get_org_trials_count')
    @patch('web.utils.route_helpers.get_org_trials')
    def test_process_organization_dashboard_request_single_org(self, mock_get_org_trials, mock_get_org_trials_count, mock_paginate, mock_compliance_counts):
        """Test processing organization dashboard request with single organization."""
        # Setup mocks
        org_ids = '42'
        
        org_trials = [{'nct_id': 'NCT001', 'status': 'Compliant'}]
        mock_get_org_trials.side_effect = [org_trials, org_trials]
        mock_get_org_trials_count.return_value = 30
        
        mock_pagination = MagicMock()
        mock_pagination.items_page = org_trials
        mock_paginate.return_value = (mock_pagination, 10)
        
        mock_compliance_counts.return_value = (1, 0)
        
        # Call function with explicit pagination parameters
        result = process_organization_dashboard_request(org_ids, page=1, per_page=10)
        
        # Verify result
        expected = {
            'template': 'dashboards/organization.html',
            'trials': org_trials,
            'pagination': mock_pagination,
            'per_page': 10,
            'org_ids': '42',
            'on_time_count': 1,
            'late_count': 0
        }
        assert result == expected
        
        # Verify mocks were called correctly
        assert mock_get_org_trials.call_count == 2
        mock_get_org_trials.assert_any_call((42,), page=1, per_page=10)
        mock_get_org_trials.assert_any_call((42,))
        mock_get_org_trials_count.assert_called_once_with((42,))
        mock_paginate.assert_called_once_with(org_trials, total_entries=30)
        mock_compliance_counts.assert_called_once_with(org_trials)


class TestParseRequestArg:
    """Test the parse_request_arg function."""
    
    def test_parse_request_arg_valid_digits(self):
        """Test parsing valid digit strings."""
        assert parse_request_arg('123') == 123
        assert parse_request_arg('0') == 0
        assert parse_request_arg('999') == 999
    
    def test_parse_request_arg_invalid_values(self):
        """Test parsing invalid values."""
        assert parse_request_arg('abc') is None
        assert parse_request_arg('') is None
        assert parse_request_arg(None) is None
        assert parse_request_arg('12.5') is None
        assert parse_request_arg('-123') is None
        assert parse_request_arg('123abc') is None


class TestProcessCompareOrganizationsRequest:
    """Test the process_compare_organizations_request function."""
    
    @patch('web.utils.route_helpers.paginate')
    @patch('web.utils.route_helpers.get_org_compliance_count')
    @patch('web.utils.route_helpers.get_org_compliance')
    def test_process_compare_organizations_request_valid_params(self, mock_get_org_compliance, mock_get_org_compliance_count, mock_paginate):
        """Test processing compare organizations request with valid parameters."""
        # Setup mocks
        org_compliance = [
            {'id': 1, 'name': 'Org1', 'on_time_count': 5, 'late_count': 2},
            {'id': 2, 'name': 'Org2', 'on_time_count': 3, 'late_count': 1}
        ]
        mock_get_org_compliance.side_effect = [org_compliance, org_compliance]
        mock_get_org_compliance_count.return_value = 20
        
        mock_pagination = MagicMock()
        mock_pagination.items_page = org_compliance
        mock_paginate.return_value = (mock_pagination, 10)
        
        # Call function with valid parameters and explicit pagination
        result = process_compare_organizations_request('80', '95', '5', '50', page=1, per_page=10)
        
        # Verify result
        expected = {
            'template': 'dashboards/compare.html',
            'org_compliance': org_compliance,
            'pagination': mock_pagination,
            'per_page': 10,
            'on_time_count': 8,  # 5 + 3
            'late_count': 3,     # 2 + 1
            'total_organizations': 2
        }
        assert result == expected
        
        # Verify mocks were called correctly
        assert mock_get_org_compliance.call_count == 2
        mock_get_org_compliance.assert_any_call(min_compliance=80, max_compliance=95, min_trials=5, max_trials=50, page=1, per_page=10)
        mock_get_org_compliance.assert_any_call(min_compliance=80, max_compliance=95, min_trials=5, max_trials=50)
        mock_get_org_compliance_count.assert_called_once_with(min_compliance=80, max_compliance=95, min_trials=5, max_trials=50)
        mock_paginate.assert_called_once_with(org_compliance, total_entries=20)

    @patch('web.utils.route_helpers.paginate')
    @patch('web.utils.route_helpers.get_org_compliance_count')
    @patch('web.utils.route_helpers.get_org_compliance')
    def test_process_compare_organizations_request_invalid_params(self, mock_get_org_compliance, mock_get_org_compliance_count, mock_paginate):
        """Test processing compare organizations request with invalid parameters."""
        # Setup mocks
        org_compliance = []
        mock_get_org_compliance.side_effect = [org_compliance, org_compliance]
        mock_get_org_compliance_count.return_value = 0
        
        mock_pagination = MagicMock()
        mock_pagination.items_page = []
        mock_paginate.return_value = (mock_pagination, 10)
        
        # Call function with invalid parameters and explicit pagination
        result = process_compare_organizations_request('invalid', '', 'not_a_number', None, page=1, per_page=10)
        
        # Verify result
        expected = {
            'template': 'dashboards/compare.html',
            'org_compliance': [],
            'pagination': mock_pagination,
            'per_page': 10,
            'on_time_count': 0,
            'late_count': 0,
            'total_organizations': 0
        }
        assert result == expected
        
        # Verify mocks were called correctly
        assert mock_get_org_compliance.call_count == 2
        mock_get_org_compliance.assert_any_call(min_compliance=None, max_compliance=None, min_trials=None, max_trials=None, page=1, per_page=10)
        mock_get_org_compliance.assert_any_call(min_compliance=None, max_compliance=None, min_trials=None, max_trials=None)
        mock_get_org_compliance_count.assert_called_once_with(min_compliance=None, max_compliance=None, min_trials=None, max_trials=None)
        mock_paginate.assert_called_once_with([], total_entries=0)

    @patch('web.utils.route_helpers.paginate')
    @patch('web.utils.route_helpers.get_org_compliance_count')
    @patch('web.utils.route_helpers.get_org_compliance')
    def test_process_compare_organizations_request_missing_counts(self, mock_get_org_compliance, mock_get_org_compliance_count, mock_paginate):
        """Test processing compare organizations request with missing count fields."""
        # Setup mocks - organizations without count fields
        org_compliance = [
            {'id': 1, 'name': 'Org1'},  # Missing on_time_count, late_count
            {'id': 2, 'name': 'Org2', 'on_time_count': 5}  # Missing late_count
        ]
        mock_get_org_compliance.side_effect = [org_compliance, org_compliance]
        mock_get_org_compliance_count.return_value = 15
        
        mock_pagination = MagicMock()
        mock_pagination.items_page = org_compliance
        mock_paginate.return_value = (mock_pagination, 10)
        
        # Call function with explicit pagination
        result = process_compare_organizations_request(None, None, None, None, page=1, per_page=10)
        
        # Verify result
        expected = {
            'template': 'dashboards/compare.html',
            'org_compliance': org_compliance,
            'pagination': mock_pagination,
            'per_page': 10,
            'on_time_count': 5,  # 0 + 5
            'late_count': 0,     # 0 + 0
            'total_organizations': 2
        }
        assert result == expected
        
        # Verify mocks were called correctly
        assert mock_get_org_compliance.call_count == 2
        mock_get_org_compliance_count.assert_called_once_with(min_compliance=None, max_compliance=None, min_trials=None, max_trials=None)
        mock_paginate.assert_called_once_with(org_compliance, total_entries=15)

    @patch('web.utils.route_helpers.paginate')
    @patch('web.utils.route_helpers.get_org_compliance_count')
    @patch('web.utils.route_helpers.get_org_compliance')
    def test_process_compare_organizations_request_zero_values(self, mock_get_org_compliance, mock_get_org_compliance_count, mock_paginate):
        """Test processing compare organizations request with zero parameter values."""
        # Setup mocks
        org_compliance = []
        mock_get_org_compliance.side_effect = [org_compliance, org_compliance]
        mock_get_org_compliance_count.return_value = 0
        
        mock_pagination = MagicMock()
        mock_pagination.items_page = []
        mock_paginate.return_value = (mock_pagination, 10)
        
        # Call function with zero values (which should be valid) and explicit pagination
        result = process_compare_organizations_request('0', '0', '0', '0', page=1, per_page=10)
        
        # Verify result
        expected = {
            'template': 'dashboards/compare.html',
            'org_compliance': [],
            'pagination': mock_pagination,
            'per_page': 10,
            'on_time_count': 0,
            'late_count': 0,
            'total_organizations': 0
        }
        assert result == expected
        
        # Verify mocks were called correctly
        assert mock_get_org_compliance.call_count == 2
        mock_get_org_compliance.assert_any_call(min_compliance=0, max_compliance=0, min_trials=0, max_trials=0, page=1, per_page=10)
        mock_get_org_compliance.assert_any_call(min_compliance=0, max_compliance=0, min_trials=0, max_trials=0)
        mock_get_org_compliance_count.assert_called_once_with(min_compliance=0, max_compliance=0, min_trials=0, max_trials=0)
        mock_paginate.assert_called_once_with([], total_entries=0)


class TestProcessUserDashboardRequest:
    """Test the process_user_dashboard_request function."""
    
    @patch('web.utils.route_helpers.compliance_counts')
    @patch('web.utils.route_helpers.paginate')
    @patch('web.utils.route_helpers.get_user_trials_count')
    @patch('web.utils.route_helpers.get_user_trials')
    def test_process_user_dashboard_request_with_trials(self, mock_get_user_trials, mock_get_user_trials_count, mock_paginate, mock_compliance_counts):
        """Test processing user dashboard request with trials."""
        # Setup mocks
        user_id = 1
        user_trials = [
            {'nct_id': 'NCT001', 'status': 'Compliant', 'email': 'user@example.com'},
            {'nct_id': 'NCT002', 'status': 'Incompliant', 'email': 'user@example.com'}
        ]
        mock_get_user_trials.side_effect = [user_trials, user_trials]
        mock_get_user_trials_count.return_value = 40
        
        mock_pagination = MagicMock()
        mock_pagination.items_page = user_trials
        mock_paginate.return_value = (mock_pagination, 10)
        
        mock_compliance_counts.return_value = (1, 1)
        
        # Call function with explicit pagination parameters
        result = process_user_dashboard_request(user_id, page=1, per_page=10)
        
        # Verify result
        expected = {
            'template': 'dashboards/user.html',
            'trials': user_trials,
            'pagination': mock_pagination,
            'per_page': 10,
            'user_id': user_id,
            'user_email': 'user@example.com',
            'on_time_count': 1,
            'late_count': 1
        }
        assert result == expected
        
        # Verify mocks were called correctly
        assert mock_get_user_trials.call_count == 2
        mock_get_user_trials.assert_any_call(user_id, page=1, per_page=10)
        mock_get_user_trials.assert_any_call(user_id)
        mock_get_user_trials_count.assert_called_once_with(user_id)
        mock_paginate.assert_called_once_with(user_trials, total_entries=40)
        mock_compliance_counts.assert_called_once_with(user_trials)

    @patch('web.utils.route_helpers.get_user_trials_count')
    @patch('web.utils.route_helpers.get_user_trials')
    def test_process_user_dashboard_request_no_trials_with_current_user(self, mock_get_user_trials, mock_get_user_trials_count):
        """Test processing user dashboard request with no trials and current user getter."""
        # Setup mocks
        user_id = 1
        mock_get_user_trials.return_value = []
        mock_get_user_trials_count.return_value = 0
        
        # Mock current user getter
        mock_user = MagicMock()
        mock_user.email = 'fallback@example.com'
        def mock_current_user_getter(uid):
            return mock_user
        
        # Call function with explicit pagination parameters
        result = process_user_dashboard_request(user_id, mock_current_user_getter, page=1, per_page=10)
        
        # Verify result
        expected = {
            'template': 'dashboards/user.html',
            'trials': [],
            'pagination': None,
            'per_page': 10,
            'user_id': user_id,
            'user_email': 'fallback@example.com'
        }
        assert result == expected
        
        # Verify mocks were called correctly
        mock_get_user_trials.assert_called_once_with(user_id, page=1, per_page=10)
        mock_get_user_trials_count.assert_called_once_with(user_id)

    @patch('web.utils.route_helpers.get_user_trials_count')
    @patch('web.utils.route_helpers.get_user_trials')
    def test_process_user_dashboard_request_no_trials_no_current_user(self, mock_get_user_trials, mock_get_user_trials_count):
        """Test processing user dashboard request with no trials and no current user getter."""
        # Setup mocks
        user_id = 1
        mock_get_user_trials.return_value = []
        mock_get_user_trials_count.return_value = 0
        
        # Call function without current user getter and with explicit pagination
        result = process_user_dashboard_request(user_id, page=1, per_page=10)
        
        # Verify result
        expected = {
            'template': 'dashboards/user.html',
            'trials': [],
            'pagination': None,
            'per_page': 10,
            'user_id': user_id,
            'user_email': None
        }
        assert result == expected
        
        # Verify mocks were called correctly
        mock_get_user_trials.assert_called_once_with(user_id, page=1, per_page=10)
        mock_get_user_trials_count.assert_called_once_with(user_id)

    @patch('web.utils.route_helpers.compliance_counts')
    @patch('web.utils.route_helpers.paginate')
    @patch('web.utils.route_helpers.get_user_trials_count')
    @patch('web.utils.route_helpers.get_user_trials')
    def test_process_user_dashboard_request_mixed_status_trials(self, mock_get_user_trials, mock_get_user_trials_count, mock_paginate, mock_compliance_counts):
        """Test processing user dashboard request with mixed status trials."""
        # Setup mocks
        user_id = 1
        user_trials = [
            {'nct_id': 'NCT001', 'status': 'Compliant', 'email': 'user@example.com'},
            {'nct_id': 'NCT002', 'status': 'Incompliant', 'email': 'user@example.com'},
            {'nct_id': 'NCT003', 'status': 'Unknown', 'email': 'user@example.com'},
            {'nct_id': 'NCT004', 'status': 'Pending', 'email': 'user@example.com'}
        ]
        mock_get_user_trials.side_effect = [user_trials, user_trials]
        mock_get_user_trials_count.return_value = 60
        
        mock_pagination = MagicMock()
        mock_pagination.items_page = user_trials
        mock_paginate.return_value = (mock_pagination, 10)
        
        # Only Compliant and Incompliant should count
        mock_compliance_counts.return_value = (1, 1)
        
        # Call function with explicit pagination parameters
        result = process_user_dashboard_request(user_id, page=1, per_page=10)
        
        # Verify result
        expected = {
            'template': 'dashboards/user.html',
            'trials': user_trials,
            'pagination': mock_pagination,
            'per_page': 10,
            'user_id': user_id,
            'user_email': 'user@example.com',
            'on_time_count': 1,
            'late_count': 1
        }
        assert result == expected
        
        # Verify mocks were called correctly
        assert mock_get_user_trials.call_count == 2
        mock_get_user_trials.assert_any_call(user_id, page=1, per_page=10)
        mock_get_user_trials.assert_any_call(user_id)
        mock_get_user_trials_count.assert_called_once_with(user_id)
        mock_paginate.assert_called_once_with(user_trials, total_entries=60)
        mock_compliance_counts.assert_called_once_with(user_trials)


class TestEdgeCases:
    """Test edge cases and error scenarios."""
    
    @patch('web.utils.route_helpers.get_org_trials_count')
    @patch('web.utils.route_helpers.get_org_trials')
    def test_organization_dashboard_with_comma_edge_cases(self, mock_get_org_trials, mock_get_org_trials_count):
        """Test organization dashboard with various comma scenarios."""
        mock_get_org_trials.return_value = []
        mock_get_org_trials_count.return_value = 0
        
        with patch('web.utils.route_helpers.paginate') as mock_paginate, \
             patch('web.utils.route_helpers.compliance_counts') as mock_compliance_counts:
            
            mock_pagination = MagicMock()
            mock_pagination.items_page = []
            mock_paginate.return_value = (mock_pagination, 10)
            mock_compliance_counts.return_value = (0, 0)
            
            # Test with trailing/leading commas and explicit pagination
            result = process_organization_dashboard_request(',1,2,3,', page=1, per_page=10)
            
            # Should filter out empty strings and process only valid IDs
            assert result['org_ids'] == ',1,2,3,'
            assert result['template'] == 'dashboards/organization.html'
            
            # Verify that get_org_trials was called with the correct tuple (filtering empty strings)
            mock_get_org_trials.assert_any_call((1, 2, 3), page=1, per_page=10)
            mock_get_org_trials_count.assert_called_once_with((1, 2, 3))

    def test_search_request_edge_cases(self):
        """Test search request with edge case parameters."""
        # Test with all None values
        search_params = {'title': None, 'nct_id': None, 'organization': None}
        compliance_status_list = []
        
        result = process_search_request(search_params, compliance_status_list, page=1, per_page=10)
        
        # Should return just the template since no search parameters
        expected = {
            'template': 'dashboards/home.html'
        }
        assert result == expected 