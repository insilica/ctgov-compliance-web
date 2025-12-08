from flask import Blueprint, render_template, stream_template, request, jsonify, make_response
from flask_login import login_required, current_user    # pragma: no cover, current_user
import csv
import io
from datetime import datetime
from .utils.route_helpers import (
    process_index_request,
    process_search_request,
    process_organization_dashboard_request,
    process_compare_organizations_request,
    process_user_dashboard_request,
    process_reporting_request,
    build_action_items_export_rows,
)
from .utils.queries import (
    QueryManager,
)
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

bp = Blueprint('routes', __name__)
qm = QueryManager()

@bp.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200

# Autocomplete API endpoints
@bp.route('/api/autocomplete/titles')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.autocomplete_titles")
def autocomplete_titles():
    """API endpoint for trial title autocomplete suggestions"""
    current_span = trace.get_current_span()
    query = request.args.get('q', '').strip()
    current_span.set_attribute("query.length", len(query))
    if len(query) < 2:
        return jsonify([])
    
    from .db import query as db_query
    sql = '''
        SELECT DISTINCT t.title
        FROM trial t
        WHERE t.title ILIKE %s
        ORDER BY t.title ASC
        LIMIT 10
        '''
    results = db_query(sql, [f"%{query}%"])
    suggestions = [row['title'] for row in results if row['title']]
    current_span.set_attribute("results.count", len(suggestions))
    return jsonify(suggestions)

@bp.route('/api/autocomplete/organizations')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.autocomplete_organizations")
def autocomplete_organizations():
    """API endpoint for organization name autocomplete suggestions"""
    current_span = trace.get_current_span()
    query = request.args.get('q', '').strip()
    current_span.set_attribute("query.length", len(query))
    if len(query) < 2:
        return jsonify([])
    
    from .db import query as db_query
    sql = '''
        SELECT DISTINCT o.name
        FROM organization o
        WHERE o.name ILIKE %s
        ORDER BY o.name ASC
        LIMIT 10
        '''
    results = db_query(sql, [f"%{query}%"])
    suggestions = [row['name'] for row in results if row['name']]
    current_span.set_attribute("results.count", len(suggestions))
    return jsonify(suggestions)

@bp.route('/api/autocomplete/nct_ids')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.autocomplete_nct_ids")
def autocomplete_nct_ids():
    """API endpoint for NCT ID autocomplete suggestions"""
    current_span = trace.get_current_span()
    query = request.args.get('q', '').strip()
    current_span.set_attribute("query.length", len(query))
    if len(query) < 3:
        return jsonify([])
    
    from .db import query as db_query
    sql = '''
        SELECT DISTINCT t.nct_id
        FROM trial t
        WHERE t.nct_id ILIKE %s
        ORDER BY t.nct_id ASC
        LIMIT 10
        '''
    results = db_query(sql, [f"%{query}%"])
    suggestions = [row['nct_id'] for row in results if row['nct_id']]
    current_span.set_attribute("results.count", len(suggestions))
    return jsonify(suggestions)

@bp.route('/api/autocomplete/user_emails')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.autocomplete_user_emails")
def autocomplete_user_emails():
    """API endpoint for user email autocomplete suggestions"""
    current_span = trace.get_current_span()
    query = request.args.get('q', '').strip()
    current_span.set_attribute("query.length", len(query))
    if len(query) < 2:
        return jsonify([])
    
    from .db import query as db_query
    sql = '''
        SELECT DISTINCT u.email
        FROM ctgov_user u
        WHERE u.email ILIKE %s
        ORDER BY u.email ASC
        LIMIT 10
        '''
    results = db_query(sql, [f"%{query}%"])
    suggestions = [row['email'] for row in results if row['email']]
    current_span.set_attribute("results.count", len(suggestions))
    return jsonify(suggestions)

@bp.route('/')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.index")
def index():
    current_span = trace.get_current_span()
    search_params = {
        'title': request.args.get('title'),
        'nct_id': request.args.get('nct_id'),
        'organization': request.args.get('organization'),
        'user_email': request.args.get('user_email'),
        'date_type': request.args.get('date_type'),
        'date_from': request.args.get('date_from'),
        'date_to': request.args.get('date_to'),
        'compliance_status': request.args.getlist('compliance_status[]')
    }
    if any(search_params.values()):
        current_span.set_attribute("params.count", sum(1 for v in search_params.values() if v))
        
        compliance_status_list = request.args.getlist('compliance_status[]')
        current_span.set_attribute("params.compliance_status_count", len(compliance_status_list))
        template_data = process_search_request(search_params, compliance_status_list, QueryManager=qm)
        return render_template(template_data['template'], **{k: v for k, v in template_data.items() if k != 'template'})
    template_data = process_index_request(QueryManager=qm)
    return render_template(template_data['template'], **{k: v for k, v in template_data.items() if k != 'template'})
    
@bp.route('/organization/<org_ids>')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.show_organization_dashboard")
def show_organization_dashboard(org_ids):
    current_span = trace.get_current_span()
    current_span.set_attribute("org_ids.length", len(org_ids))
    template_data = process_organization_dashboard_request(org_ids, QueryManager=qm)
    return render_template(template_data['template'], **{k: v for k, v in template_data.items() if k != 'template'})

@bp.route('/compare')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.show_compare_organizations_dashboard")
def show_compare_organizations_dashboard():
    current_span = trace.get_current_span()
    min_compliance = request.args.get('min_compliance')
    max_compliance = request.args.get('max_compliance')
    min_trials = request.args.get('min_trials')
    max_trials = request.args.get('max_trials')
    
    template_data = process_compare_organizations_request(min_compliance, max_compliance, min_trials, max_trials, QueryManager=qm)
    return render_template(template_data['template'], **{k: v for k, v in template_data.items() if k != 'template'})

@bp.route('/user/<int:user_id>')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.show_user_dashboard")
def show_user_dashboard(user_id):
    current_span = trace.get_current_span()
    current_span.set_attribute("user.id", int(user_id))
    def current_user_getter(uid):
        return current_user.get(uid)
    
    template_data = process_user_dashboard_request(user_id, current_user_getter, QueryManager=qm)
    return render_template(template_data['template'], **{k: v for k, v in template_data.items() if k != 'template'})

@bp.route('/reporting')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.reporting_dashboard")
def reporting_dashboard():
    current_span = trace.get_current_span()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    focus_org_id = request.args.get('org_focus', type=int)
    action_page = request.args.get('action_page', default=1, type=int)
    if start_date:
        current_span.set_attribute("filters.start_date", start_date)
    if end_date:
        current_span.set_attribute("filters.end_date", end_date)
    filter_args = {
        'min_compliance': request.args.get('min_compliance'),
        'max_compliance': request.args.get('max_compliance'),
        'funding_source_class': request.args.get('funding_source_class'),
        'organization': request.args.get('organization')
    }
    template_data = process_reporting_request(
        start_date,
        end_date,
        filters=filter_args,
        focus_org_id=focus_org_id,
        action_page=action_page,
        QueryManager=qm
    )
    return stream_template(template_data['template'], **{k: v for k, v in template_data.items() if k != 'template'})

@bp.route('/reporting/action-items/export')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.reporting_action_items_export")
def reporting_action_items_export():
    current_span = trace.get_current_span()
    filter_args = {
        'min_compliance': request.args.get('min_compliance'),
        'max_compliance': request.args.get('max_compliance'),
        'funding_source_class': request.args.get('funding_source_class'),
        'organization': request.args.get('organization')
    }
    rows = build_action_items_export_rows(filters=filter_args, QueryManager=qm)
    current_span.set_attribute("export.rows", len(rows))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Sponsor Name',
        'Trial Title',
        'NCT ID',
        'Status',
        'Start Date',
        'Completion Date',
        'Days Overdue'
    ])

    def _fmt(date_value):
        return date_value.strftime('%m/%d/%Y') if date_value else ''

    for row in rows:
        writer.writerow([
            row.get('organization_name', ''),
            row.get('title', ''),
            row.get('nct_id', ''),
            row.get('status', ''),
            _fmt(row.get('start_date')),
            _fmt(row.get('completion_date')),
            row.get('days_overdue', 0)
        ])

    csv_content = output.getvalue()
    output.close()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"action_items_{timestamp}.csv"
    response = make_response(csv_content)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@bp.route('/api/reporting/time-series')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.reporting_time_series")
def reporting_time_series():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    filter_args = {
        'min_compliance': request.args.get('min_compliance'),
        'max_compliance': request.args.get('max_compliance'),
        'funding_source_class': request.args.get('funding_source_class'),
        'organization': request.args.get('organization')
    }
    data = process_reporting_request(start_date, end_date, filters=filter_args, focus_org_id=None, QueryManager=qm)
    return jsonify({
        'time_series': data['time_series'],
        'status_keys': data['status_keys'],
        'start_date': data['start_date'],
        'end_date': data['end_date'],
        'kpis': data['kpis']
    })

# CSV Export Route
@bp.route('/export/csv')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.export_csv")
def export_csv():
    """Export current filtered data to CSV"""
    current_span = trace.get_current_span()
    # Get the same parameters as other routes
    search_params = {
        'title': request.args.get('title'),
        'nct_id': request.args.get('nct_id'),
        'organization': request.args.get('organization'),
        'user_email': request.args.get('user_email'),
        'date_type': request.args.get('date_type'),
        'date_from': request.args.get('date_from'),
        'date_to': request.args.get('date_to')
    }
    current_span.set_attribute("params.count", sum(1 for v in search_params.values() if v))
    
    compliance_status_list = request.args.getlist('compliance_status[]')
    export_type = request.args.get('type', 'trials')  # Default to trials export
    current_span.set_attribute("export.type", export_type)
    current_span.set_attribute("params.compliance_status_count", len(compliance_status_list))
    
    # Get data based on export type
    if export_type == 'organizations':
        min_compliance = request.args.get('min_compliance')
        max_compliance = request.args.get('max_compliance')
        min_trials = request.args.get('min_trials')
        max_trials = request.args.get('max_trials')
        funding_source_class = request.args.get('funding_source_class')
        organization_name = request.args.get('organization')
        
        org_compliance = qm.get_organization_risk_analysis(
            min_compliance=min_compliance,
            max_compliance=max_compliance,
            min_trials=min_trials,
            max_trials=max_trials,
            funding_source_class=funding_source_class,
            organization_name=organization_name
        )
        data = org_compliance
        filename = 'organizations_compliance_export'
        
        # Define CSV headers for organizations
        headers = [
            'Organization Name',
            'Total Trials',
            'Compliant Trials',
            'Non-Compliant Trials',
            'Pending Trials',
            'Compliance Rate (%)',
            'High Risk Trials',
            'Average Days Overdue'
        ]
        
        # Format data for CSV
        csv_data = []
        for org in data:
            compliance_rate = ((org.get('on_time_count', 0) / org.get('total_trials', 1) * 100) if org.get('total_trials', 0) > 0 else 0)
            avg_days_overdue = ((org.get('total_overdue_days', 0) / org.get('late_count', 1)) if org.get('late_count', 0) > 0 else 0)
            
            csv_data.append([
                org.get('name', ''),
                org.get('total_trials', 0),
                org.get('on_time_count', 0),
                org.get('late_count', 0),
                org.get('pending_count', 0),
                round(compliance_rate, 1),
                org.get('high_risk_trials', 0),
                round(avg_days_overdue, 1) if avg_days_overdue > 0 else 0
            ])
            
    elif export_type == 'user':
        user_id = request.args.get('user_id')
        if user_id:
            def current_user_getter(uid):
                return current_user.get(uid)
            template_data = process_user_dashboard_request(int(user_id), current_user_getter, QueryManager=qm)
            data = template_data.get('trials', [])
            filename = f'user_{user_id}_trials_export'
        else:
            template_data = process_search_request(search_params, compliance_status_list, QueryManager=qm)
            data = template_data.get('trials', [])
            filename = 'trials_export'
            
    else:
        # Default to trials export
        if any(search_params.values()) or compliance_status_list:
            template_data = process_search_request(search_params, compliance_status_list, QueryManager=qm)
        else:
            template_data = process_index_request(QueryManager=qm)
            
        data = template_data.get('trials', [])
        filename = 'trials_export'
    
    # For trials data (default case and user case)
    if export_type != 'organizations':
        # Define CSV headers for trials
        headers = [
            'Title',
            'NCT ID',
            'Organization',
            'User Email',
            'Status',
            'Start Date',
            'End Date',
            'Reporting Due Date'
        ]
        
        # Format data for CSV
        csv_data = []
        for trial in data:
            csv_data.append([
                trial.get('title', ''),
                trial.get('nct_id', ''),
                trial.get('name', ''),
                trial.get('email', ''),
                trial.get('status', ''),
                trial.get('start_date').strftime('%m/%d/%Y') if trial.get('start_date') else '',
                trial.get('completion_date').strftime('%m/%d/%Y') if trial.get('completion_date') else '',
                trial.get('reporting_due_date').strftime('%m/%d/%Y') if trial.get('reporting_due_date') else ''
            ])
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(headers)
    
    # Write data
    for row in csv_data:
        writer.writerow(row)
    
    # Create response
    csv_content = output.getvalue()
    output.close()
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename_with_timestamp = f"{filename}_{timestamp}.csv"
    current_span.set_attribute("export.rows", len(csv_data))
    
    # Create response with proper headers
    response = make_response(csv_content)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename_with_timestamp}"'
    
    return response

# Print Report Routes
@bp.route('/report/print')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.print_report")
def print_report():
    """Generate a printable report based on current search/filter criteria"""
    current_span = trace.get_current_span()
    # Get search parameters from request (same as search route)
    search_params = {
        'title': request.args.get('title'),
        'nct_id': request.args.get('nct_id'),
        'organization': request.args.get('organization'),
        'user_email': request.args.get('user_email'),
        'date_type': request.args.get('date_type'),
        'date_from': request.args.get('date_from'),
        'date_to': request.args.get('date_to')
    }
    
    compliance_status_list = request.args.getlist('compliance_status[]')
    report_type = request.args.get('type', 'trials')  # Default to trials report
    current_span.set_attribute("report.type", report_type)
    
    # Process based on report type with enhanced analytics
    if report_type == 'organizations':
        min_compliance = request.args.get('min_compliance')
        max_compliance = request.args.get('max_compliance')
        min_trials = request.args.get('min_trials')
        max_trials = request.args.get('max_trials')
        funding_source_class = request.args.get('funding_source_class')
        organization_name = request.args.get('organization')
        
        # Use enhanced organization analysis
        org_compliance = qm.get_organization_risk_analysis(
            min_compliance=min_compliance,
            max_compliance=max_compliance,
            min_trials=min_trials,
            max_trials=max_trials,
            funding_source_class=funding_source_class,
            organization_name=organization_name
        )
        template_data = {
            'org_compliance': org_compliance,
            'on_time_count': sum(org.get('on_time_count', 0) for org in org_compliance),
            'late_count': sum(org.get('late_count', 0) for org in org_compliance),
        }
        
        # Get organization-level critical issues
        template_data['critical_issues'] = []
        for org in org_compliance:
            if org.get('high_risk_trials', 0) > 0:
                template_data['critical_issues'].append({
                    'type': 'High Risk Organization',
                    'priority': 'High',
                    'organization': org.get('name'),
                    'high_risk_trials': org.get('high_risk_trials'),
                    'description': f"{org.get('name')} has {org.get('high_risk_trials')} high-risk trials requiring attention"
                })
        
    elif report_type == 'user':
        user_id = request.args.get('user_id')
        if user_id:
            def current_user_getter(uid):
                return current_user.get(uid)
            template_data = process_user_dashboard_request(int(user_id), current_user_getter, QueryManager=qm)
        else:
            template_data = process_search_request(search_params, compliance_status_list, QueryManager=qm)
            
        # Get enhanced analytics for user data
        if template_data.get('trials'):
            enhanced_stats = qm.get_compliance_summary_stats(search_params, compliance_status_list)
            template_data.update(enhanced_stats)
            template_data['critical_issues'] = qm.get_critical_issues(search_params, compliance_status_list)
    else:
        # Default to trials report with enhanced analytics
        if any(search_params.values()) or compliance_status_list:
            template_data = process_search_request(search_params, compliance_status_list, QueryManager=qm)
        else:
            template_data = process_index_request(QueryManager=qm)
        
        # Get enhanced trial analytics
        enhanced_trials = qm.get_enhanced_trial_analytics(search_params, compliance_status_list)
        enhanced_stats = qm.get_compliance_summary_stats(search_params, compliance_status_list)
        critical_issues = qm.get_critical_issues(search_params, compliance_status_list)
        
        # Update template data with enhanced information
        template_data.update(enhanced_stats)
        template_data['enhanced_trials'] = enhanced_trials
        template_data['critical_issues'] = critical_issues
    
    # Add report metadata
    from datetime import datetime
    template_data['report_generated'] = datetime.now()
    template_data['report_type'] = report_type
    template_data['search_params'] = search_params
    template_data['compliance_status_list'] = compliance_status_list
    
    return render_template('reports/print_report.html', **{k: v for k, v in template_data.items() if k != 'template'})
