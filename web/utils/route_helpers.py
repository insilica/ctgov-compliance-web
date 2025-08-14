"""
Route helper functions that contain the core business logic for each route.

These functions are extracted from the route handlers to enable easier testing
without Flask context dependencies while maintaining clean separation of concerns.
"""

from urllib.parse import unquote
from .queries import QueryManager
from .pagination import paginate, get_pagination_args
from opentelemetry import trace

tracer = trace.get_tracer(__name__)


@tracer.start_as_current_span("route_helpers.compliance_counts")
def compliance_counts(rates):
    """Calculate compliance counts from trials data using pandas."""
    current_span = trace.get_current_span()
    # Defer pandas import to function level
    c = rates[0]['compliant_count']
    ic = rates[0]['incompliant_count']
    current_span.set_attribute("compliance.compliant_count", str(c))
    current_span.set_attribute("compliance.incompliant_count", str(ic))
    return c, ic


@tracer.start_as_current_span("route_helpers.process_index_request")
def process_index_request(page=None, per_page=None, QueryManager=QueryManager()):
    """Process the index page request and return template data."""
    current_span = trace.get_current_span()
    # Get pagination parameters from request if not provided
    if page is None or per_page is None:
        page, per_page = get_pagination_args()
    current_span.set_attribute("pagination.page", str(page))
    current_span.set_attribute("pagination.per_page", str(per_page))

    # Get paginated trials and total count
    trials = QueryManager.get_all_trials(page=page, per_page=per_page)
    total_count = QueryManager.get_all_trials(count="COUNT(trial_id)")[0]['count']
    current_span.set_attribute("trials.total_count", str(total_count))

    # Get compliance counts using SQL aggregation
    rates = QueryManager.get_compliance_rate()
    on_time_count, late_count = compliance_counts(rates)
    current_span.set_attribute("compliance.on_time_count", str(on_time_count))
    current_span.set_attribute("compliance.late_count", str(late_count))

    pagination, per_page = paginate(trials, total_entries=total_count)

    return {
        'template': 'dashboards/home.html',
        'trials': pagination.items_page,
        'pagination': pagination,
        'per_page': per_page,
        'on_time_count': on_time_count,
        'late_count': late_count
    }


@tracer.start_as_current_span("route_helpers.process_search_request")
def process_search_request(search_params, compliance_status_list, page=None, per_page=None, QueryManager=QueryManager()):
    """Process a search request and return template data."""
    current_span = trace.get_current_span()
    # If there are any search parameters, perform the search
    if any(search_params.values()) or compliance_status_list:
        # Get pagination parameters from request if not provided
        if page is None or per_page is None:
            page, per_page = get_pagination_args()
        current_span.set_attribute("pagination.page", page)
        current_span.set_attribute("pagination.per_page", per_page)

        # Get paginated search results and total count
        search_results = QueryManager.search_trials(search_params, page=page, per_page=per_page)
        total_count = QueryManager.search_trials(search_params, count="COUNT(trial_id)")[0]['count']
        current_span.set_attribute("trials.total_count", total_count)

        # Get compliance counts using SQL aggregation
        rates = QueryManager.get_compliance_rate()
        on_time_count, late_count = compliance_counts(rates)
        current_span.set_attribute("compliance.on_time_count", str(on_time_count))
        current_span.set_attribute("compliance.late_count", str(late_count))

        pagination, per_page = paginate(search_results, total_entries=total_count)

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


@tracer.start_as_current_span("route_helpers.process_organization_dashboard_request")
def process_organization_dashboard_request(org_ids, page=None, per_page=None, QueryManager=QueryManager()):
    """Process organization dashboard request and return template data."""
    current_span = trace.get_current_span()
    # Convert org_ids to a tuple of integers
    decoded_org_ids = unquote(unquote(org_ids))
    org_list = tuple(int(id) for id in decoded_org_ids.split(',') if id)
    current_span.set_attribute("org.ids.count", len(org_list))
    
    # Get pagination parameters from request if not provided
    if page is None or per_page is None:
        page, per_page = get_pagination_args()
    current_span.set_attribute("pagination.page", page)
    current_span.set_attribute("pagination.per_page", per_page)
    
    # Get paginated organization trials and total count
    org_trials = QueryManager.get_org_trials(org_list, page=page, per_page=per_page)
    total_count = QueryManager.get_org_trials(org_list, count="COUNT(trial_id)")[0]['count']
    current_span.set_attribute("trials.total_count", total_count)
    
    # Get all organization trials for compliance counts
    compliance_rates = QueryManager.get_compliance_rate("organization_id IN %s", org_list)
    
    pagination, per_page = paginate(org_trials, total_entries=total_count)
    
    on_time_count, late_count = compliance_counts(compliance_rates)
    current_span.set_attribute("compliance.on_time_count", str(on_time_count))
    current_span.set_attribute("compliance.late_count", str(late_count))

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


@tracer.start_as_current_span("route_helpers.process_compare_organizations_request")
def process_compare_organizations_request(min_compliance, max_compliance, min_trials, max_trials, page=None, per_page=None, QueryManager=QueryManager()):
    """Process compare organizations request and return template data."""
    current_span = trace.get_current_span()
    # Parse arguments
    parsed_min_compliance = parse_request_arg(min_compliance)
    parsed_max_compliance = parse_request_arg(max_compliance)
    parsed_min_trials = parse_request_arg(min_trials)
    parsed_max_trials = parse_request_arg(max_trials)
    current_span.set_attribute("filters.min_compliance", parsed_min_compliance if parsed_min_compliance is not None else -1)
    current_span.set_attribute("filters.max_compliance", parsed_max_compliance if parsed_max_compliance is not None else -1)
    current_span.set_attribute("filters.min_trials", parsed_min_trials if parsed_min_trials is not None else -1)
    current_span.set_attribute("filters.max_trials", parsed_max_trials if parsed_max_trials is not None else -1)

    # Get pagination parameters from request if not provided
    if page is None or per_page is None:
        page, per_page = get_pagination_args()
    current_span.set_attribute("pagination.page", page)
    current_span.set_attribute("pagination.per_page", per_page)
    
    # Get paginated organization compliance and total count
    org_compliance = QueryManager.get_org_compliance(
        min_compliance=parsed_min_compliance,
        max_compliance=parsed_max_compliance,
        min_trials=parsed_min_trials,
        max_trials=parsed_max_trials,
        page=page,
        per_page=per_page
    )

    total_count = QueryManager.get_org_compliance(
        min_compliance=parsed_min_compliance,
        max_compliance=parsed_max_compliance,
        min_trials=parsed_min_trials,
        max_trials=parsed_max_trials,
        count="COUNT(id)"
    )[0]['count']
    current_span.set_attribute("organizations.total_count", total_count)
    
    # Get all organization compliance for summary counts
    all_org_compliance = QueryManager.get_compliance_rate_compare(
        min_compliance=parsed_min_compliance,
        max_compliance=parsed_max_compliance,
        min_trials=parsed_min_trials,
        max_trials=parsed_max_trials
    )
    
    pagination, per_page = paginate(org_compliance, total_entries=total_count)

    on_time_count, late_count = compliance_counts(all_org_compliance)
    current_span.set_attribute("compliance.on_time_count", str(on_time_count))
    current_span.set_attribute("compliance.late_count", str(late_count))

    return {
        'template': 'dashboards/compare.html',
        'org_compliance': pagination.items_page,
        'pagination': pagination,
        'per_page': per_page,
        'on_time_count': on_time_count,
        'late_count': late_count,
        'total_organizations': total_count
    }


@tracer.start_as_current_span("route_helpers.process_user_dashboard_request")
def process_user_dashboard_request(user_id, current_user_getter=None, page=None, per_page=None, QueryManager=QueryManager()):
    """Process user dashboard request and return template data."""
    current_span = trace.get_current_span()
    current_span.set_attribute("user.id", user_id)
    # Get pagination parameters from request if not provided
    if page is None or per_page is None:
        page, per_page = get_pagination_args()
    current_span.set_attribute("pagination.page", page)
    current_span.set_attribute("pagination.per_page", per_page)
    
    # Get paginated user trials and total count
    user_trials = QueryManager.get_user_trials(user_id, page=page, per_page=per_page)
    total_count = QueryManager.get_user_trials(user_id, count="COUNT(trial_id)")[0]['count']
    current_span.set_attribute("trials.total_count", total_count)
    
    if user_trials:
        user_email = user_trials[0]['email']
        
        # Get all user trials for compliance counts
        all_user_trials = QueryManager.get_user_trials(user_id)
        
        pagination, per_page = paginate(user_trials, total_entries=total_count)

        on_time_count, late_count = compliance_counts(all_user_trials)
        current_span.set_attribute("compliance.on_time_count", str(on_time_count))
        current_span.set_attribute("compliance.late_count", str(late_count))

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
            'per_page': per_page if per_page is not None else 25,
            'user_id': user_id,
            'user_email': user_email
        }
