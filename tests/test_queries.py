import pytest
from unittest.mock import patch
from flask import Flask
from web.utils.queries import (
    get_all_trials, get_org_trials, get_user_trials, 
    search_trials, get_org_compliance
)


@pytest.fixture
def mock_query():
    with patch('web.utils.queries.query') as mock:
        yield mock


def test_get_all_trials(mock_query):
    expected_data = [{'nct_id': 'NCT123', 'title': 'Test Trial'}]
    mock_query.return_value = expected_data
    
    result = get_all_trials()
    
    assert result == expected_data
    mock_query.assert_called_once()
    # Verify SQL contains expected tables
    sql = mock_query.call_args[0][0]
    assert 'trial t' in sql
    assert 'trial_compliance tc' in sql
    assert 'organization o' in sql
    assert 'ctgov_user u' in sql


def test_get_org_trials(mock_query):
    expected_data = [{'nct_id': 'NCT123', 'name': 'Org1'}]
    mock_query.return_value = expected_data
    
    result = get_org_trials((1, 2))
    
    assert result == expected_data
    mock_query.assert_called_once()
    # Verify SQL and parameters
    sql, params = mock_query.call_args[0]
    assert 'o.id IN %s' in sql
    assert params == [(1, 2)]


def test_get_user_trials(mock_query):
    expected_data = [{'nct_id': 'NCT123', 'email': 'user@example.com'}]
    mock_query.return_value = expected_data
    
    result = get_user_trials(1)
    
    assert result == expected_data
    mock_query.assert_called_once()
    # Verify SQL and parameters
    sql, params = mock_query.call_args[0]
    assert 'u.id = %s' in sql
    assert params == [1]


def test_search_trials_basic(mock_query):
    expected_data = [{'nct_id': 'NCT123'}]
    mock_query.return_value = expected_data
    
    app = Flask(__name__)
    with app.test_request_context():
        # Test with basic search params
        result = search_trials({
            'title': 'Test',
            'nct_id': None,
            'organization': None,
            'user_email': None,
            'date_type': None,
            'date_from': None,
            'date_to': None
        })
        
        assert result == expected_data
        mock_query.assert_called_once()
        # Verify SQL contains title search
        sql, params = mock_query.call_args[0]
        assert "t.title ILIKE %s" in sql
        assert params == ["%Test%"]


def test_search_trials_complex(mock_query):
    expected_data = [{'nct_id': 'NCT123'}]
    mock_query.return_value = expected_data
    
    app = Flask(__name__)
    with app.test_request_context('/?compliance_status[]=compliant&compliance_status[]=incompliant'):
        # Test with multiple search params
        result = search_trials({
            'title': 'Test',
            'nct_id': 'NCT',
            'organization': 'Org',
            'user_email': 'user@example.com',
            'date_type': 'completion',
            'date_from': '2022-01-01',
            'date_to': '2022-12-31'
        })
        
        assert result == expected_data
        mock_query.assert_called_once()
        
        # Verify SQL contains all search conditions
        sql, params = mock_query.call_args[0]
        assert "t.title ILIKE %s" in sql
        assert "t.nct_id ILIKE %s" in sql
        assert "o.name ILIKE %s" in sql
        assert "u.email ILIKE %s" in sql
        assert "t.completion_date >= %s" in sql
        assert "t.completion_date <= %s" in sql
        assert "tc.status = 'Compliant'" in sql
        assert "tc.status = 'Incompliant'" in sql
        
        # Verify params contain expected values
        assert "%Test%" in params
        assert "%NCT%" in params
        assert "%Org%" in params
        assert "%user@example.com%" in params
        assert "2022-01-01" in params
        assert "2022-12-31" in params


def test_get_org_compliance_no_filters(mock_query):
    expected_data = [{'id': 1, 'name': 'Org1', 'total_trials': 10}]
    mock_query.return_value = expected_data
    
    result = get_org_compliance()
    
    assert result == expected_data
    mock_query.assert_called_once()
    # Verify SQL has no HAVING clause
    sql, params = mock_query.call_args[0]
    assert 'HAVING' not in sql
    assert params == []


def test_get_org_compliance_with_filters(mock_query):
    expected_data = [{'id': 1, 'name': 'Org1', 'total_trials': 10}]
    mock_query.return_value = expected_data
    
    result = get_org_compliance(
        min_compliance=50,
        max_compliance=90,
        min_trials=5,
        max_trials=20
    )
    
    assert result == expected_data
    mock_query.assert_called_once()
    
    # Verify SQL has HAVING clause with all filters
    sql, params = mock_query.call_args[0]
    assert 'HAVING' in sql
    assert len(params) == 4
    assert params[0] == 50  # min_compliance
    assert params[1] == 90  # max_compliance
    assert params[2] == 5   # min_trials
    assert params[3] == 20  # max_trials
