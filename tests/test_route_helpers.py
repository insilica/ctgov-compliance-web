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
        mock_qm.get_trial_cumulative_time_series.return_value = [
            {
                'period_start': date(2024, 1, 1),
                'compliance_status': 'Compliant',
                'trials_in_month': 2,
                'cumulative_trials': 2,
                'new_trials': 2,
                'completed_trials': 1,
                'avg_reporting_delay_days': 5.5,
                'reporting_delay_trials': 1
            },
            {
                'period_start': '2024-02-01',
                'compliance_status': 'Incompliant',
                'trials_in_month': 1,
                'cumulative_trials': 1,
                'new_trials': 1,
                'completed_trials': 0,
                'avg_reporting_delay_days': None,
                'reporting_delay_trials': 0
            },
        ]
        mock_qm.get_reporting_metrics.return_value = [{
            'total_trials': 3,
            'compliant_count': 2,
            'trials_with_issues_count': 1,
            'avg_reporting_delay_days': 4
        }]
        mock_qm.get_organization_risk_analysis.return_value = [
            {
                'id': 1,
                'name': 'Org A',
                'total_trials': 5,
                'on_time_count': 3,
                'late_count': 2,
                'pending_count': 0,
                'high_risk_trials': 1
            }
        ]
        mock_qm.get_org_incompliant_trials.return_value = []
        mock_qm.get_funding_source_classes.return_value = ['Academic', 'Industry']

        result = process_reporting_request('2024-01-01', '2024-03-15', QueryManager=mock_qm)

        mock_qm.get_trial_cumulative_time_series.assert_called_once_with(
            start_date='2024-01-01',
            end_date='2024-03-15'
        )
        mock_qm.get_reporting_metrics.assert_called_once()
        mock_qm.get_organization_risk_analysis.assert_called_once_with(
            min_compliance=None,
            max_compliance=None,
            funding_source_class=None,
            organization_name=None
        )
        mock_qm.get_org_incompliant_trials.assert_not_called()
        mock_qm.get_funding_source_classes.assert_called_once()
        assert result['template'] == 'reporting.html'
        assert result['start_date'] == '2024-01-01'
        assert result['end_date'] == '2024-03-15'
        assert len(result['time_series']) == 3
        first_month = result['time_series'][0]
        assert first_month['date'] == '2024-01-01'
        assert first_month['statuses']['compliant']['monthly'] == 2
        assert first_month['statuses']['compliant']['cumulative'] == 2
        assert first_month['statuses']['incompliant']['monthly'] == 0
        assert first_month['statuses']['incompliant']['cumulative'] == 0
        second_month = result['time_series'][1]
        assert second_month['statuses']['compliant']['cumulative'] == 2
        assert second_month['statuses']['incompliant']['cumulative'] == 1
        third_month = result['time_series'][2]
        assert third_month['statuses']['compliant']['cumulative'] == 2
        assert third_month['statuses']['incompliant']['cumulative'] == 1
        assert result['latest_point']['date'] == '2024-03-01'
        assert result['status_keys']
        assert 'statuses' in result['latest_point']
        assert first_month['new_trials'] == 2
        assert first_month['completed_trials'] == 1
        assert first_month['avg_reporting_delay_days'] == 5.5
        assert third_month['avg_reporting_delay_days'] is None
        assert result['kpis']['total_trials'] == 3
        assert result['action_items']
        assert result['action_items'][0]['name'] == 'Org A'
        assert result['action_items_per_page'] == 7
        pagination = result['action_items_pagination']
        assert pagination.total_entries == 1
        assert pagination.page == 1
        assert pagination.total_pages == 1
        assert pagination.start_index == 1
        assert pagination.end_index == 1
        assert result['action_filter_values'] == {
            'min_compliance': '',
            'max_compliance': '',
            'funding_source_class': '',
            'organization': ''
        }
        assert result['action_filter_options']['funding_source_classes'] == ['Academic', 'Industry']

    @patch('web.utils.route_helpers.date')
    def test_reporting_request_defaults(self, mock_date_cls):
        mock_date_cls.today.return_value = date(2024, 4, 30)
        mock_date_cls.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
        mock_qm = MagicMock()
        mock_qm.get_trial_cumulative_time_series.return_value = []
        mock_qm.get_reporting_metrics.return_value = [{'total_trials': 0, 'compliant_count': 0, 'trials_with_issues_count': 0, 'avg_reporting_delay_days': 0}]
        mock_qm.get_organization_risk_analysis.return_value = []
        mock_qm.get_org_incompliant_trials.return_value = []
        mock_qm.get_funding_source_classes.return_value = []

        result = process_reporting_request(QueryManager=mock_qm)

        assert result['end_date'] == '2024-04-30'
        assert result['start_date'] == '2024-04-01'
        mock_qm.get_trial_cumulative_time_series.assert_called_once_with(
            start_date='2024-04-01',
            end_date='2024-04-30'
        )
        mock_qm.get_reporting_metrics.assert_called_once()
        mock_qm.get_organization_risk_analysis.assert_called_once_with(
            min_compliance=None,
            max_compliance=None,
            funding_source_class=None,
            organization_name=None
        )
        mock_qm.get_org_incompliant_trials.assert_not_called()
        mock_qm.get_funding_source_classes.assert_called_once()
        assert result['kpis']['total_trials'] == 0
        assert result['action_items'] == []
        assert result['action_items_per_page'] == 7
        assert result['action_items_pagination'].total_entries == 0
        assert result['action_items_pagination'].page == 1

    def test_reporting_request_swaps_dates(self):
        mock_qm = MagicMock()
        mock_qm.get_trial_cumulative_time_series.return_value = []
        mock_qm.get_reporting_metrics.return_value = [{'total_trials': 1, 'compliant_count': 1, 'trials_with_issues_count': 0, 'avg_reporting_delay_days': 0}]
        mock_qm.get_organization_risk_analysis.return_value = []
        mock_qm.get_org_incompliant_trials.return_value = []
        mock_qm.get_funding_source_classes.return_value = []

        result = process_reporting_request('2024-03-10', '2024-03-01', QueryManager=mock_qm)

        assert result['start_date'] == '2024-03-01'
        assert result['end_date'] == '2024-03-10'
        mock_qm.get_trial_cumulative_time_series.assert_called_once_with(
            start_date='2024-03-01',
            end_date='2024-03-10'
        )
        mock_qm.get_reporting_metrics.assert_called_once()
        mock_qm.get_organization_risk_analysis.assert_called_once_with(
            min_compliance=None,
            max_compliance=None,
            funding_source_class=None,
            organization_name=None
        )
        mock_qm.get_org_incompliant_trials.assert_not_called()
        mock_qm.get_funding_source_classes.assert_called_once()
        assert result['kpis']['overall_compliance_rate'] == 100.0
        assert result['action_items'] == []
        assert result['action_items_pagination'].total_entries == 0

    def test_reporting_request_with_filters(self):
        mock_qm = MagicMock()
        mock_qm.get_trial_cumulative_time_series.return_value = []
        mock_qm.get_reporting_metrics.return_value = [{'total_trials': 0, 'compliant_count': 0, 'trials_with_issues_count': 0, 'avg_reporting_delay_days': 0}]
        mock_qm.get_organization_risk_analysis.return_value = [
            {
                'id': 2,
                'name': 'Org Focus',
                'total_trials': 3,
                'on_time_count': 1,
                'late_count': 2,
                'pending_count': 0,
                'high_risk_trials': 0
            }
        ]
        mock_qm.get_org_incompliant_trials.return_value = []
        mock_qm.get_funding_source_classes.return_value = ['Academic']
        filters = {
            'min_compliance': '75',
            'max_compliance': '90',
            'funding_source_class': 'Academic',
            'organization': 'Health'
        }

        process_reporting_request(filters=filters, QueryManager=mock_qm)

        mock_qm.get_organization_risk_analysis.assert_called_once_with(
            min_compliance=75,
            max_compliance=90,
            funding_source_class='Academic',
            organization_name='Health'
        )
        mock_qm.get_org_incompliant_trials.assert_not_called()

    def test_reporting_request_focus_org_details(self):
        mock_qm = MagicMock()
        mock_qm.get_trial_cumulative_time_series.return_value = []
        mock_qm.get_reporting_metrics.return_value = [{'total_trials': 0, 'compliant_count': 0, 'trials_with_issues_count': 0, 'avg_reporting_delay_days': 0}]
        mock_qm.get_organization_risk_analysis.return_value = [
            {
                'id': 5,
                'name': 'Org Modal',
                'total_trials': 4,
                'on_time_count': 1,
                'late_count': 3,
                'pending_count': 0,
                'high_risk_trials': 0
            }
        ]
        mock_qm.get_org_incompliant_trials.return_value = [
            {
                'id': 10,
                'title': 'Trial 1',
                'nct_id': 'NCT123',
                'organization_name': 'Org Modal',
                'user_email': 'user@example.com',
                'status': 'Incompliant',
                'start_date': date(2024, 1, 1),
                'completion_date': date(2024, 2, 1)
            }
        ]
        mock_qm.get_funding_source_classes.return_value = []

        result = process_reporting_request(focus_org_id=5, QueryManager=mock_qm)

        mock_qm.get_org_incompliant_trials.assert_called_once_with(5)
        assert result['focused_org']['id'] == 5
        assert result['focused_org_trials'][0]['nct_id'] == 'NCT123'

    def test_reporting_request_action_items_paginated(self):
        mock_qm = MagicMock()
        mock_qm.get_trial_cumulative_time_series.return_value = []
        mock_qm.get_reporting_metrics.return_value = [{'total_trials': 0, 'compliant_count': 0, 'trials_with_issues_count': 0, 'avg_reporting_delay_days': 0}]
        org_rows = []
        for idx in range(1, 9):
            org_rows.append({
                'id': idx,
                'name': f'Org {idx}',
                'total_trials': 10,
                'on_time_count': idx,
                'late_count': 10 - idx,
                'pending_count': 0,
                'high_risk_trials': 0
            })
        mock_qm.get_organization_risk_analysis.return_value = org_rows
        mock_qm.get_org_incompliant_trials.return_value = []
        mock_qm.get_funding_source_classes.return_value = []

        result = process_reporting_request(action_page=2, QueryManager=mock_qm)

        assert len(result['action_items']) == 1
        assert result['action_items'][0]['name'] == 'Org 8'
        pagination = result['action_items_pagination']
        assert pagination.page == 2
        assert pagination.total_pages == 2
        assert pagination.total_entries == 8
        assert pagination.start_index == 8
        assert pagination.end_index == 8

        result_last_page = process_reporting_request(action_page=5, QueryManager=mock_qm)
        assert result_last_page['action_items_pagination'].page == 2
