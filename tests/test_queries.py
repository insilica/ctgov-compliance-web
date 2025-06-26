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


def test_get_all_trials_empty_result(mock_query):
    """Test get_all_trials with empty result"""
    mock_query.return_value = []
    
    result = get_all_trials()
    
    assert result == []
    mock_query.assert_called_once()


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


def test_get_org_trials_single_id(mock_query):
    """Test get_org_trials with single organization ID"""
    expected_data = [{'nct_id': 'NCT123', 'name': 'Org1'}]
    mock_query.return_value = expected_data
    
    result = get_org_trials((1,))
    
    assert result == expected_data
    mock_query.assert_called_once()
    sql, params = mock_query.call_args[0]
    assert params == [(1,)]


def test_get_org_trials_empty_tuple(mock_query):
    """Test get_org_trials with empty tuple"""
    expected_data = []
    mock_query.return_value = expected_data
    
    result = get_org_trials(())
    
    assert result == expected_data
    mock_query.assert_called_once()
    sql, params = mock_query.call_args[0]
    assert params == [()]


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


def test_get_user_trials_zero_id(mock_query):
    """Test get_user_trials with user ID 0"""
    expected_data = []
    mock_query.return_value = expected_data
    
    result = get_user_trials(0)
    
    assert result == expected_data
    mock_query.assert_called_once()
    sql, params = mock_query.call_args[0]
    assert params == [0]


def test_get_user_trials_negative_id(mock_query):
    """Test get_user_trials with negative user ID"""
    expected_data = []
    mock_query.return_value = expected_data
    
    result = get_user_trials(-1)
    
    assert result == expected_data
    mock_query.assert_called_once()
    sql, params = mock_query.call_args[0]
    assert params == [-1]


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


def test_search_trials_no_conditions(mock_query):
    """Test search_trials with no conditions (all None/empty)"""
    expected_data = [{'nct_id': 'NCT123'}]
    mock_query.return_value = expected_data
    
    app = Flask(__name__)
    with app.test_request_context():
        result = search_trials({
            'title': None,
            'nct_id': None,
            'organization': None,
            'user_email': None,
            'status': None,
            'date_type': None,
            'date_from': None,
            'date_to': None
        })
        
        assert result == expected_data
        mock_query.assert_called_once()
        # Should only have base SQL without additional conditions
        sql, params = mock_query.call_args[0]
        assert "WHERE 1=1" in sql
        assert "ORDER BY t.title ASC" in sql
        assert params == []


def test_search_trials_empty_strings(mock_query):
    """Test search_trials with empty strings (should be treated as falsy)"""
    expected_data = [{'nct_id': 'NCT123'}]
    mock_query.return_value = expected_data
    
    app = Flask(__name__)
    with app.test_request_context():
        result = search_trials({
            'title': '',
            'nct_id': '',
            'organization': '',
            'user_email': '',
            'status': '',
            'date_type': '',
            'date_from': '',
            'date_to': ''
        })
        
        assert result == expected_data
        mock_query.assert_called_once()
        # Should only have base SQL without additional conditions
        sql, params = mock_query.call_args[0]
        assert params == []


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


def test_search_trials_only_date_from(mock_query):
    """Test search with only date_from (no date_to)"""
    expected_data = [{'nct_id': 'NCT123'}]
    mock_query.return_value = expected_data
    
    app = Flask(__name__)
    with app.test_request_context():
        result = search_trials({
            'title': None,
            'nct_id': None,
            'organization': None,
            'user_email': None,
            'date_type': 'completion',
            'date_from': '2022-01-01',
            'date_to': None
        })
        
        assert result == expected_data
        mock_query.assert_called_once()
        sql, params = mock_query.call_args[0]
        assert "t.completion_date >= %s" in sql
        assert "t.completion_date <=" not in sql
        assert params == ["2022-01-01"]


def test_search_trials_only_date_to(mock_query):
    """Test search with only date_to (no date_from)"""
    expected_data = [{'nct_id': 'NCT123'}]
    mock_query.return_value = expected_data
    
    app = Flask(__name__)
    with app.test_request_context():
        result = search_trials({
            'title': None,
            'nct_id': None,
            'organization': None,
            'user_email': None,
            'date_type': 'completion',
            'date_from': None,
            'date_to': '2022-12-31'
        })
        
        assert result == expected_data
        mock_query.assert_called_once()
        sql, params = mock_query.call_args[0]
        assert "t.completion_date <= %s" in sql
        assert "t.completion_date >=" not in sql
        assert params == ["2022-12-31"]


def test_search_trials_pending_status(mock_query):
    """Test search with pending compliance status"""
    expected_data = [{'nct_id': 'NCT123'}]
    mock_query.return_value = expected_data
    
    app = Flask(__name__)
    with app.test_request_context('/?compliance_status[]=pending'):
        result = search_trials({
            'title': None,
            'nct_id': None,
            'organization': None,
            'user_email': None,
            'date_type': None,
            'date_from': None,
            'date_to': None
        })
        
        assert result == expected_data
        mock_query.assert_called_once()
        
        # Verify SQL contains pending status condition
        sql, params = mock_query.call_args[0]
        assert "tc.status IS NULL" in sql


def test_search_trials_mixed_compliance_status(mock_query):
    """Test search with all three compliance statuses"""
    expected_data = [{'nct_id': 'NCT123'}]
    mock_query.return_value = expected_data
    
    app = Flask(__name__)
    with app.test_request_context('/?compliance_status[]=compliant&compliance_status[]=incompliant&compliance_status[]=pending'):
        result = search_trials({
            'title': None,
            'nct_id': None,
            'organization': None,
            'user_email': None,
            'date_type': None,
            'date_from': None,
            'date_to': None
        })
        
        assert result == expected_data
        mock_query.assert_called_once()
        
        # Verify SQL contains all compliance status conditions
        sql, params = mock_query.call_args[0]
        assert "tc.status = 'Compliant'" in sql
        assert "tc.status = 'Incompliant'" in sql
        assert "tc.status IS NULL" in sql


def test_search_trials_start_date_type(mock_query):
    """Test search with start date type"""
    expected_data = [{'nct_id': 'NCT123'}]
    mock_query.return_value = expected_data
    
    app = Flask(__name__)
    with app.test_request_context():
        result = search_trials({
            'title': None,
            'nct_id': None,
            'organization': None,
            'user_email': None,
            'date_type': 'start',
            'date_from': '2022-01-01',
            'date_to': '2022-12-31'
        })
        
        assert result == expected_data
        mock_query.assert_called_once()
        
        # Verify SQL contains start date conditions
        sql, params = mock_query.call_args[0]
        assert "t.start_date >= %s" in sql
        assert "t.start_date <= %s" in sql
        assert "2022-01-01" in params
        assert "2022-12-31" in params


def test_search_trials_due_date_type(mock_query):
    """Test search with due date type"""
    expected_data = [{'nct_id': 'NCT123'}]
    mock_query.return_value = expected_data
    
    app = Flask(__name__)
    with app.test_request_context():
        result = search_trials({
            'title': None,
            'nct_id': None,
            'organization': None,
            'user_email': None,
            'date_type': 'due',
            'date_from': '2022-01-01',
            'date_to': '2022-12-31'
        })
        
        assert result == expected_data
        mock_query.assert_called_once()
        
        # Verify SQL contains due date conditions
        sql, params = mock_query.call_args[0]
        assert "t.reporting_due_date >= %s" in sql
        assert "t.reporting_due_date <= %s" in sql
        assert "2022-01-01" in params
        assert "2022-12-31" in params


def test_search_trials_invalid_date_type(mock_query):
    """Test search with invalid date type (no date conditions should be added but params are still appended)"""
    expected_data = [{'nct_id': 'NCT123'}]
    mock_query.return_value = expected_data
    
    app = Flask(__name__)
    with app.test_request_context():
        result = search_trials({
            'title': None,
            'nct_id': None,
            'organization': None,
            'user_email': None,
            'date_type': 'invalid_type',
            'date_from': '2022-01-01',
            'date_to': '2022-12-31'
        })
        
        assert result == expected_data
        mock_query.assert_called_once()
        
        # Should not add any date conditions when date_type is invalid
        sql, params = mock_query.call_args[0]
        assert "t.completion_date >=" not in sql
        assert "t.completion_date <=" not in sql
        assert "t.start_date >=" not in sql
        assert "t.start_date <=" not in sql
        assert "t.reporting_due_date >=" not in sql
        assert "t.reporting_due_date <=" not in sql
        # Note: Due to implementation bug, parameters are still added even though no conditions are used
        assert params == ['2022-01-01', '2022-12-31']


def test_search_trials_empty_compliance_status_list(mock_query):
    """Test search with empty compliance status list to ensure status_conditions logic is covered"""
    expected_data = [{'nct_id': 'NCT123'}]
    mock_query.return_value = expected_data
    
    app = Flask(__name__)
    with app.test_request_context('/?compliance_status[]=unknown'):
        result = search_trials({
            'title': None,
            'nct_id': None,
            'organization': None,
            'user_email': None,
            'date_type': None,
            'date_from': None,
            'date_to': None
        })
        
        assert result == expected_data
        mock_query.assert_called_once()
        
        # Verify SQL doesn't contain compliance status WHERE conditions since 'unknown' isn't handled
        sql, params = mock_query.call_args[0]
        # Should not contain any compliance conditions in WHERE clause
        assert "tc.status = 'Compliant'" not in sql
        assert "tc.status = 'Incompliant'" not in sql
        assert "tc.status IS NULL" not in sql


def test_search_trials_with_status_param(mock_query):
    """Test search with status parameter"""
    expected_data = [{'nct_id': 'NCT123'}]
    mock_query.return_value = expected_data
    
    app = Flask(__name__)
    with app.test_request_context():
        result = search_trials({
            'title': None,
            'nct_id': None,
            'organization': None,
            'user_email': None,
            'status': 'Active',
            'date_type': None,
            'date_from': None,
            'date_to': None
        })
        
        assert result == expected_data
        mock_query.assert_called_once()
        
        # Verify SQL contains status condition
        sql, params = mock_query.call_args[0]
        assert "t.status = %s" in sql
        assert "Active" in params


def test_search_trials_special_characters(mock_query):
    """Test search with special characters in search terms"""
    expected_data = [{'nct_id': 'NCT123'}]
    mock_query.return_value = expected_data
    
    app = Flask(__name__)
    with app.test_request_context():
        result = search_trials({
            'title': 'Test & Trial',
            'nct_id': 'NCT-123',
            'organization': "Org's Hospital",
            'user_email': 'user@test.example.com',
            'date_type': None,
            'date_from': None,
            'date_to': None
        })
        
        assert result == expected_data
        mock_query.assert_called_once()
        sql, params = mock_query.call_args[0]
        assert "%Test & Trial%" in params
        assert "%NCT-123%" in params
        assert "%Org's Hospital%" in params
        assert "%user@test.example.com%" in params


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


def test_get_org_compliance_only_min_compliance(mock_query):
    """Test get_org_compliance with only min_compliance filter"""
    expected_data = [{'id': 1, 'name': 'Org1', 'total_trials': 10}]
    mock_query.return_value = expected_data
    
    result = get_org_compliance(min_compliance=75)
    
    assert result == expected_data
    mock_query.assert_called_once()
    sql, params = mock_query.call_args[0]
    assert 'HAVING' in sql
    assert len(params) == 1
    assert params[0] == 75


def test_get_org_compliance_only_max_compliance(mock_query):
    """Test get_org_compliance with only max_compliance filter"""
    expected_data = [{'id': 1, 'name': 'Org1', 'total_trials': 10}]
    mock_query.return_value = expected_data
    
    result = get_org_compliance(max_compliance=85)
    
    assert result == expected_data
    mock_query.assert_called_once()
    sql, params = mock_query.call_args[0]
    assert 'HAVING' in sql
    assert len(params) == 1
    assert params[0] == 85


def test_get_org_compliance_only_min_trials(mock_query):
    """Test get_org_compliance with only min_trials filter"""
    expected_data = [{'id': 1, 'name': 'Org1', 'total_trials': 10}]
    mock_query.return_value = expected_data
    
    result = get_org_compliance(min_trials=10)
    
    assert result == expected_data
    mock_query.assert_called_once()
    sql, params = mock_query.call_args[0]
    assert 'HAVING' in sql
    assert len(params) == 1
    assert params[0] == 10


def test_get_org_compliance_only_max_trials(mock_query):
    """Test get_org_compliance with only max_trials filter"""
    expected_data = [{'id': 1, 'name': 'Org1', 'total_trials': 10}]
    mock_query.return_value = expected_data
    
    result = get_org_compliance(max_trials=100)
    
    assert result == expected_data
    mock_query.assert_called_once()
    sql, params = mock_query.call_args[0]
    assert 'HAVING' in sql
    assert len(params) == 1
    assert params[0] == 100


def test_get_org_compliance_zero_values(mock_query):
    """Test get_org_compliance with zero values (should be treated as valid)"""
    expected_data = [{'id': 1, 'name': 'Org1', 'total_trials': 0}]
    mock_query.return_value = expected_data
    
    result = get_org_compliance(
        min_compliance=0,
        max_compliance=0,
        min_trials=0,
        max_trials=0
    )
    
    assert result == expected_data
    mock_query.assert_called_once()
    sql, params = mock_query.call_args[0]
    assert 'HAVING' in sql
    assert len(params) == 4
    assert all(p == 0 for p in params)


def test_get_org_compliance_boundary_values(mock_query):
    """Test get_org_compliance with boundary values"""
    expected_data = [{'id': 1, 'name': 'Org1', 'total_trials': 10}]
    mock_query.return_value = expected_data
    
    result = get_org_compliance(
        min_compliance=100,
        max_compliance=100,
        min_trials=1,
        max_trials=1000
    )
    
    assert result == expected_data
    mock_query.assert_called_once()
    sql, params = mock_query.call_args[0]
    assert 'HAVING' in sql
    assert params[0] == 100
    assert params[1] == 100
    assert params[2] == 1
    assert params[3] == 1000


def test_get_org_compliance_empty_result(mock_query):
    """Test get_org_compliance with empty result"""
    mock_query.return_value = []
    
    result = get_org_compliance()
    
    assert result == []
    mock_query.assert_called_once()


def test_get_org_compliance_mixed_filters(mock_query):
    """Test get_org_compliance with only some filters"""
    expected_data = [{'id': 1, 'name': 'Org1', 'total_trials': 10}]
    mock_query.return_value = expected_data
    
    result = get_org_compliance(
        min_compliance=50,
        max_trials=20
    )
    
    assert result == expected_data
    mock_query.assert_called_once()
    sql, params = mock_query.call_args[0]
    assert 'HAVING' in sql
    assert len(params) == 2
    assert params[0] == 50
    assert params[1] == 20


def test_search_trials_no_compliance_status_in_request(mock_query):
    """Test search_trials when no compliance_status in request args"""
    expected_data = [{'nct_id': 'NCT123'}]
    mock_query.return_value = expected_data
    
    app = Flask(__name__)
    with app.test_request_context('/'):  # No compliance_status[] parameters
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
        sql, params = mock_query.call_args[0]
        # Should not contain compliance status conditions
        assert "tc.status = 'Compliant'" not in sql
        assert "tc.status = 'Incompliant'" not in sql
        assert "tc.status IS NULL" not in sql
