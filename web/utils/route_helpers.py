"""
Route helper functions that contain the core business logic for each route.

These functions are extracted from the route handlers to enable easier testing
without Flask context dependencies while maintaining clean separation of concerns.
"""

from urllib.parse import unquote
from .queries import get_all_trials, get_org_trials, get_org_compliance, get_user_trials, search_trials
from .pagination import paginate


def compliance_counts(trials):
    """Calculate compliance counts from trials data using pandas."""
    # Defer pandas import to function level
    import pandas as pd
    
    # Convert to DataFrame for status counts
    df = pd.DataFrame(trials)
    
    # Count statuses
    status_counts = df['status'].value_counts() if not df.empty else pd.Series()
    on_time_count = status_counts.get('Compliant', 0)
    late_count = status_counts.get('Incompliant', 0)

    return on_time_count, late_count


def process_index_request():
    """Process the index page request and return template data."""
    trials = get_all_trials()
    pagination, per_page = paginate(trials)
    
    on_time_count, late_count = compliance_counts(trials)
    
    return {
        'template': 'dashboards/home.html',
        'trials': pagination.items_page,
        'pagination': pagination,
        'per_page': per_page,
        'on_time_count': on_time_count,
        'late_count': late_count
    }


def process_search_request(search_params, compliance_status_list):
    """Process a search request and return template data."""
    # If there are any search parameters, perform the search
    if any(search_params.values()) or compliance_status_list:
        search_results = search_trials(search_params)
        pagination, per_page = paginate(search_results)
        
        on_time_count, late_count = compliance_counts(search_results)
        
        return {
            'template': 'dashboards/home.html',
            'trials': pagination.items_page,
            'pagination': pagination,
            'per_page': per_page,
            'on_time_count': on_time_count,
            'late_count': late_count,
            'is_search': True
        }
    
    # If no search parameters, just show the search form
    return {
        'template': 'dashboards/home.html'
    }


def process_organization_dashboard_request(org_ids):
    """Process organization dashboard request and return template data."""
    # Convert org_ids to a tuple of integers
    decoded_org_ids = unquote(unquote(org_ids))
    org_list = tuple(int(id) for id in decoded_org_ids.split(',') if id)
    org_trials = get_org_trials(org_list)
    pagination, per_page = paginate(org_trials)
    
    on_time_count, late_count = compliance_counts(org_trials)

    return {
        'template': 'dashboards/organization.html',
        'trials': pagination.items_page,
        'pagination': pagination,
        'per_page': per_page,
        'org_ids': decoded_org_ids,
        'on_time_count': on_time_count,
        'late_count': late_count
    }


def parse_request_arg(val):
    """Parse a request argument into an integer if valid, otherwise return None."""
    return int(val) if val and val.isdigit() else None


def process_compare_organizations_request(min_compliance, max_compliance, min_trials, max_trials):
    """Process compare organizations request and return template data."""
    # Parse arguments
    parsed_min_compliance = parse_request_arg(min_compliance)
    parsed_max_compliance = parse_request_arg(max_compliance)
    parsed_min_trials = parse_request_arg(min_trials)
    parsed_max_trials = parse_request_arg(max_trials)

    org_compliance = get_org_compliance(
        min_compliance=parsed_min_compliance,
        max_compliance=parsed_max_compliance,
        min_trials=parsed_min_trials,
        max_trials=parsed_max_trials
    )
    pagination, per_page = paginate(org_compliance)

    on_time_count = sum(org.get('on_time_count', 0) for org in org_compliance)
    late_count = sum(org.get('late_count', 0) for org in org_compliance)
    total_organizations = len(org_compliance)

    return {
        'template': 'dashboards/compare.html',
        'org_compliance': pagination.items_page,
        'pagination': pagination,
        'per_page': per_page,
        'on_time_count': on_time_count,
        'late_count': late_count,
        'total_organizations': total_organizations
    }


def process_user_dashboard_request(user_id, current_user_getter=None):
    """Process user dashboard request and return template data."""
    user_trials = get_user_trials(user_id)
    if user_trials:
        user_email = user_trials[0]['email']
        pagination, per_page = paginate(user_trials)

        on_time_count, late_count = compliance_counts(user_trials)

        return {
            'template': 'dashboards/user.html',
            'trials': pagination.items_page,
            'pagination': pagination,
            'per_page': per_page,
            'user_id': user_id,
            'user_email': user_email,
            'on_time_count': on_time_count,
            'late_count': late_count
        }
    else:
        # Use the current_user_getter function if provided, otherwise None
        user_email = current_user_getter(user_id).email if current_user_getter else None
        return {
            'template': 'dashboards/user.html',
            'trials': [],
            'pagination': None,
            'per_page': 25,
            'user_id': user_id,
            'user_email': user_email
        } 