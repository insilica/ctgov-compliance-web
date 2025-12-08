"""
Route helper functions that contain the core business logic for each route.

These functions are extracted from the route handlers to enable easier testing
without Flask context dependencies while maintaining clean separation of concerns.
"""

from urllib.parse import unquote
from datetime import date, datetime, timedelta
from .queries import QueryManager
from .pagination import paginate, get_pagination_args, Pagination
from .reporting_metrics import build_reporting_kpis
from opentelemetry import trace

tracer = trace.get_tracer(__name__)
REPORTING_WINDOW_DAYS = 30
DEFAULT_STATUS_ORDER = ['Compliant', 'Incompliant', 'Pending']
ACTION_ITEMS_PER_PAGE = 7



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


def _extract_action_filter_params(filters=None):
    """Normalize sidebar filter params for the action items list."""
    filters = filters or {}

    def _clean_int(value):
        value = value.strip() if isinstance(value, str) else None
        return int(value) if value and value.isdigit() else None

    def _clean_text(value):
        return value.strip() if isinstance(value, str) else ''

    min_compliance_raw = filters.get('min_compliance')
    max_compliance_raw = filters.get('max_compliance')
    funding_source_raw = filters.get('funding_source_class')
    organization_raw = filters.get('organization')

    query_filters = {
        'min_compliance': _clean_int(min_compliance_raw) if min_compliance_raw is not None else None,
        'max_compliance': _clean_int(max_compliance_raw) if max_compliance_raw is not None else None,
        'funding_source_class': _clean_text(funding_source_raw) or None,
        'organization': _clean_text(organization_raw) or None
    }

    form_values = {
        'min_compliance': _clean_text(min_compliance_raw) if min_compliance_raw is not None else '',
        'max_compliance': _clean_text(max_compliance_raw) if max_compliance_raw is not None else '',
        'funding_source_class': _clean_text(funding_source_raw) if funding_source_raw is not None else '',
        'organization': _clean_text(organization_raw) if organization_raw is not None else ''
    }

    return query_filters, form_values


def _parse_iso_date(value):
    """Parse YYYY-MM-DD strings into date objects."""
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None


def _coerce_to_date(value):
    """Attempt to convert incoming values into date objects."""
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            return None
    return None


def _start_of_month(dt):
    """Return the first day of the month for the given date."""
    return dt.replace(day=1)


def _add_one_month(dt):
    """Return a date representing the first day of the next month."""
    if dt.month == 12:
        return date(dt.year + 1, 1, 1)
    return date(dt.year, dt.month + 1, 1)


@tracer.start_as_current_span("route_helpers.process_reporting_request")
def process_reporting_request(start_date=None, end_date=None, filters=None, focus_org_id=None, action_page=None, action_per_page=ACTION_ITEMS_PER_PAGE, QueryManager=QueryManager()):
    """Build template context for the reporting dashboard."""
    current_span = trace.get_current_span()
    filter_params, filter_form_values = _extract_action_filter_params(filters)
    current_span.set_attribute("reporting.filters.min_compliance", filter_params.get('min_compliance') if filter_params.get('min_compliance') is not None else -1)
    current_span.set_attribute("reporting.filters.max_compliance", filter_params.get('max_compliance') if filter_params.get('max_compliance') is not None else -1)
    if filter_params.get('funding_source_class'):
        current_span.set_attribute("reporting.filters.funding_source_class", filter_params['funding_source_class'])
    if filter_params.get('organization'):
        current_span.set_attribute("reporting.filters.organization", filter_params['organization'])
    start_dt = _parse_iso_date(start_date)
    end_dt = _parse_iso_date(end_date)

    today = date.today()
    if not end_dt:
        end_dt = today
    if not start_dt:
        start_dt = end_dt - timedelta(days=REPORTING_WINDOW_DAYS - 1)

    if start_dt > end_dt:
        start_dt, end_dt = end_dt, start_dt

    start_of_month = _start_of_month(start_dt)
    end_of_month = _add_one_month(_start_of_month(end_dt))

    start_iso = start_dt.isoformat()
    end_iso = end_dt.isoformat()
    current_span.set_attribute("reporting.start_date", start_iso)
    current_span.set_attribute("reporting.end_date", end_iso)

    rows = QueryManager.get_trial_cumulative_time_series(start_date=start_iso, end_date=end_iso)
    kpi_rows = QueryManager.get_reporting_metrics() or []
    kpis = build_reporting_kpis(kpi_rows[0] if kpi_rows else None)
    current_span.set_attribute("reporting.total_trials", kpis.get('total_trials', 0))
    current_span.set_attribute("reporting.compliance_rate", kpis.get('overall_compliance_rate', 0))
    org_compliance_rows = QueryManager.get_organization_risk_analysis(
        min_compliance=filter_params.get('min_compliance'),
        max_compliance=filter_params.get('max_compliance'),
        funding_source_class=filter_params.get('funding_source_class'),
        organization_name=filter_params.get('organization')
    )
    funding_source_options = QueryManager.get_funding_source_classes()
    action_items_all = _build_org_action_items(org_compliance_rows)
    total_action_items = len(action_items_all)
    current_span.set_attribute("reporting.action_items", total_action_items)
    focused_org = None
    focused_org_trials = []
    normalized_page = action_page if isinstance(action_page, int) and action_page > 0 else 1
    per_page = action_per_page if isinstance(action_per_page, int) and action_per_page > 0 else ACTION_ITEMS_PER_PAGE
    if focus_org_id:
        for item in action_items_all:
            if item.get('id') == focus_org_id:
                focused_org = item
                break
        if focused_org:
            trial_rows = QueryManager.get_org_incompliant_trials(focus_org_id)
            focused_org_trials = _serialize_org_trials(trial_rows)
            current_span.set_attribute("reporting.focus_org", focus_org_id)
            current_span.set_attribute("reporting.focus_org_trials", len(focused_org_trials))

    if total_action_items:
        max_page = max(1, (total_action_items + per_page - 1) // per_page)
        normalized_page = min(normalized_page, max_page)
        start_index = (normalized_page - 1) * per_page
    else:
        normalized_page = 1
        start_index = 0
    end_index = start_index + per_page
    action_items_page = action_items_all[start_index:end_index]
    action_items_pagination = Pagination(action_items_page, normalized_page, per_page, total_entries=total_action_items)

    status_order = list(DEFAULT_STATUS_ORDER)
    monthly_lookup = {}
    for row in rows:
        row_date = _coerce_to_date(row.get('period_start'))
        status_label = row.get('compliance_status') or 'Pending'
        if status_label not in status_order:
            status_order.append(status_label)
        if not row_date:
            continue
        iso_day = row_date.isoformat()
        month_entry = monthly_lookup.setdefault(iso_day, {
            'statuses': {},
            'metrics': {
                'new_trials': None,
                'completed_trials': None,
                'avg_reporting_delay_days': None,
                'reporting_delay_trials': None
            }
        })
        month_entry['statuses'][status_label] = {
            'trials_in_month': row.get('trials_in_month', 0) or 0,
            'cumulative_trials': row.get('cumulative_trials', 0) or 0
        }
        metrics = month_entry['metrics']
        new_trials = row.get('new_trials')
        if metrics['new_trials'] is None and new_trials is not None:
            metrics['new_trials'] = new_trials or 0
        completed_trials = row.get('completed_trials')
        if metrics['completed_trials'] is None and completed_trials is not None:
            metrics['completed_trials'] = completed_trials or 0
        avg_delay = row.get('avg_reporting_delay_days')
        if metrics['avg_reporting_delay_days'] is None and avg_delay is not None:
            metrics['avg_reporting_delay_days'] = avg_delay
        delay_trials = row.get('reporting_delay_trials')
        if metrics['reporting_delay_trials'] is None and delay_trials is not None:
            metrics['reporting_delay_trials'] = delay_trials or 0

    status_keys = {label: label.lower().replace(' ', '_') for label in status_order}
    cumulative_tracker = {status_keys[label]: 0 for label in status_order}

    time_series = []
    month_cursor = start_of_month
    while month_cursor < end_of_month:
        iso_day = month_cursor.isoformat()
        label = month_cursor.strftime('%B %Y')
        month_data = monthly_lookup.get(iso_day, {})
        month_metrics = month_data.get('metrics', {}) if month_data else {}
        status_bucket = month_data.get('statuses', {}) if month_data else {}
        status_payload = {}
        total_monthly = 0
        total_cumulative = 0

        for status_label in status_order:
            status_key = status_keys[status_label]
            stats = status_bucket.get(status_label, {})
            monthly_count = stats.get('trials_in_month', 0) or 0
            cumulative_count = stats.get('cumulative_trials')
            if cumulative_count is None:
                cumulative_count = cumulative_tracker[status_key]
            status_payload[status_key] = {
                'label': status_label,
                'monthly': monthly_count,
                'cumulative': cumulative_count
            }
            cumulative_tracker[status_key] = cumulative_count
            total_monthly += monthly_count
            total_cumulative += cumulative_count

        entry = {
            'date': iso_day,
            'month_label': label,
            'statuses': status_payload,
            'total_monthly': total_monthly,
            'total_cumulative': total_cumulative,
            'new_trials': month_metrics.get('new_trials', 0) or 0,
            'completed_trials': month_metrics.get('completed_trials', 0) or 0,
            'avg_reporting_delay_days': month_metrics.get('avg_reporting_delay_days'),
            'reporting_delay_trials': month_metrics.get('reporting_delay_trials', 0) or 0
        }
        time_series.append(entry)
        month_cursor = _add_one_month(month_cursor)

    context = {
        'template': 'reporting.html',
        'time_series': time_series,
        'status_keys': [{'label': label, 'key': status_keys[label]} for label in status_order],
        'start_date': start_iso,
        'end_date': end_iso,
        'latest_point': time_series[-1] if time_series else None,
        'kpis': kpis,
        'action_items': action_items_pagination.items_page,
        'action_items_pagination': action_items_pagination,
        'action_items_per_page': per_page,
        'action_filter_values': filter_form_values,
        'action_filter_options': {
            'funding_source_classes': funding_source_options
        },
        'focused_org': focused_org,
        'focused_org_trials': focused_org_trials,
        'focus_org_id': focus_org_id
    }
    current_span.set_attribute("reporting.data_points", len(time_series))
    return context


def _build_org_action_items(org_rows):
    """Create structured action items for organizations below 100% compliance."""
    action_items = []
    if not org_rows:
        return action_items

    for org in org_rows:
        total_trials = org.get('total_trials') or 0
        if not total_trials:
            continue
        on_time = org.get('on_time_count') or 0
        compliance_rate = round((on_time / total_trials) * 100, 1)
        if compliance_rate >= 100:
            continue
        late = org.get('late_count') or 0
        pending = org.get('pending_count') or 0
        high_risk = org.get('high_risk_trials') or 0

        actions = []
        if late:
            actions.append({
                'label': f"Email reporting lead about {late} late trial{'s' if late != 1 else ''}",
                'type': 'email'
            })
        if not actions:
            actions.append({
                'label': 'Contact organization to confirm reporting cadence',
                'type': 'email'
            })

        action_items.append({
            'id': org.get('id'),
            'name': org.get('name') or 'Unnamed organization',
            'compliance_rate': compliance_rate,
            'late_count': late,
            'pending_count': pending,
            'high_risk_trials': high_risk,
            'total_trials': total_trials,
            'last_compliance_check': org.get('last_compliance_check'),
            'actions': actions
        })

    # Sort by lowest compliance to highlight riskiest first
    action_items.sort(key=lambda org: org.get('compliance_rate', 100))
    return action_items


def _serialize_org_trials(rows):
    """Prepare organization trial rows for modal display."""
    serialized = []
    for row in rows or []:
        start = _coerce_to_date(row.get('start_date'))
        completion = _coerce_to_date(row.get('completion_date'))
        serialized.append({
            'id': row.get('id'),
            'title': row.get('title'),
            'nct_id': row.get('nct_id'),
            'organization_name': row.get('organization_name'),
            'user_email': row.get('user_email'),
            'status': row.get('status'),
            'start_date': start.isoformat() if start else None,
            'start_date_label': start.strftime('%b %d, %Y') if start else '—',
            'completion_date': completion.isoformat() if completion else None,
            'completion_date_label': completion.strftime('%b %d, %Y') if completion else '—',
            'days_overdue': row.get('days_overdue') or 0
        })
    return serialized


def _build_summary_tiles(latest_point, kpis, months_tracked, first_month_label):
    """Build the six-tile grid that sits beside the date filter."""
    tiles = []
    month_label = latest_point.get('month_label') if latest_point else None
    cumulative_total = latest_point.get('total_cumulative', 0) if latest_point else 0
    statuses = latest_point.get('statuses', {}) if latest_point else {}
    compliant_status = statuses.get('compliant', {})

    tiles.append({
        'label': 'Cumulative trials',
        'value': cumulative_total,
        'subtext': f"Through {month_label}" if month_label else None
    })
    tiles.append({
        'label': 'Compliant trials',
        'value': compliant_status.get('cumulative', 0),
        'subtext': f"+{compliant_status.get('monthly', 0)} this month" if month_label else None
    })
    tiles.append({
        'label': 'Total trials',
        'value': kpis.get('total_trials', 0),
        'subtext': 'All time'
    })
    tiles.append({
        'label': 'Compliance rate',
        'value': f"{kpis.get('overall_compliance_rate', 0)}%",
        'subtext': 'Overall'
    })
    tiles.append({
        'label': 'Trials with issues',
        'value': kpis.get('trials_with_issues_count', 0),
        'subtext': f"{kpis.get('trials_with_issues_pct', 0)}% of total"
    })
    tiles.append({
        'label': 'Months tracked',
        'value': months_tracked,
        'subtext': f"Since {first_month_label}" if first_month_label else None
    })
    return tiles


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
        user_email = user_trials[0]['user_email']
        
        # Get all user trials for compliance counts
        compliance_rates = QueryManager.get_compliance_rate("user_id = %s", user_id)

        pagination, per_page = paginate(user_trials, total_entries=total_count)

        on_time_count, late_count = compliance_counts(compliance_rates)
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
