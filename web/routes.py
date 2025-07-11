from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required    # pragma: no cover, current_user
from .utils.route_helpers import (
    process_index_request,
    process_search_request,
    process_organization_dashboard_request,
    process_compare_organizations_request,
    process_user_dashboard_request,
    compliance_counts
)
from .utils.queries import (
    get_enhanced_trial_analytics,
    get_compliance_summary_stats,
    get_critical_issues,
    get_organization_risk_analysis
)

bp = Blueprint('routes', __name__)

@bp.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200

@bp.route('/')
@login_required    # pragma: no cover
def index():
    template_data = process_index_request()
    return render_template(template_data['template'], **{k: v for k, v in template_data.items() if k != 'template'})

@bp.route('/home')
@login_required    # pragma: no cover
def search():
    # Get search parameters from request
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
    template_data = process_search_request(search_params, compliance_status_list)
    return render_template(template_data['template'], **{k: v for k, v in template_data.items() if k != 'template'})

@bp.route('/organization/<org_ids>')
@login_required    # pragma: no cover
def show_organization_dashboard(org_ids):
    template_data = process_organization_dashboard_request(org_ids)
    return render_template(template_data['template'], **{k: v for k, v in template_data.items() if k != 'template'})

@bp.route('/compare')
@login_required    # pragma: no cover
def show_compare_organizations_dashboard():
    min_compliance = request.args.get('min_compliance')
    max_compliance = request.args.get('max_compliance')
    min_trials = request.args.get('min_trials')
    max_trials = request.args.get('max_trials')

    template_data = process_compare_organizations_request(min_compliance, max_compliance, min_trials, max_trials)
    return render_template(template_data['template'], **{k: v for k, v in template_data.items() if k != 'template'})

@bp.route('/user/<int:user_id>')
@login_required    # pragma: no cover
def show_user_dashboard(user_id):
    def current_user_getter(uid):
        return current_user.get(uid)
    
    template_data = process_user_dashboard_request(user_id, current_user_getter)
    return render_template(template_data['template'], **{k: v for k, v in template_data.items() if k != 'template'})

# Print Report Routes
@bp.route('/report/print')
@login_required    # pragma: no cover
def print_report():
    """Generate a printable report based on current search/filter criteria"""
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
    
    # Process based on report type with enhanced analytics
    if report_type == 'organizations':
        min_compliance = request.args.get('min_compliance')
        max_compliance = request.args.get('max_compliance')
        min_trials = request.args.get('min_trials')
        max_trials = request.args.get('max_trials')
        
        # Use enhanced organization analysis
        org_compliance = get_organization_risk_analysis(min_compliance, max_compliance, min_trials, max_trials)
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
            template_data = process_user_dashboard_request(int(user_id), current_user_getter)
        else:
            template_data = process_search_request(search_params, compliance_status_list)
            
        # Get enhanced analytics for user data
        if template_data.get('trials'):
            enhanced_stats = get_compliance_summary_stats(search_params, compliance_status_list)
            template_data.update(enhanced_stats)
            template_data['critical_issues'] = get_critical_issues(search_params, compliance_status_list)
    else:
        # Default to trials report with enhanced analytics
        if any(search_params.values()) or compliance_status_list:
            template_data = process_search_request(search_params, compliance_status_list)
        else:
            template_data = process_index_request()
        
        # Get enhanced trial analytics
        enhanced_trials = get_enhanced_trial_analytics(search_params, compliance_status_list)
        enhanced_stats = get_compliance_summary_stats(search_params, compliance_status_list)
        critical_issues = get_critical_issues(search_params, compliance_status_list)
        
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
