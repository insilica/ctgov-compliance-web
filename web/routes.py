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
