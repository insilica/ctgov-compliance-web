from urllib.parse import unquote
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from .db import query
from .utils.pagination import paginate
import pandas as pd
from datetime import datetime
from .utils.queries import get_all_trials, get_org_trials, get_org_compliance, get_user_trials, search_trials

bp = Blueprint('routes', __name__)

@bp.route('/')
@login_required
def index():
    trials = get_all_trials()
    pagination, per_page = paginate(trials)
    
    # Convert to DataFrame for status counts
    df = pd.DataFrame(trials)
    
    # Count statuses
    status_counts = df['status'].value_counts() if not df.empty else pd.Series()
    on_time_count = status_counts.get('Compliant', 0)
    late_count = status_counts.get('Incompliant', 0)
    
    return render_template('dashboards/home.html',
                         trials=pagination.items_page,
                         pagination=pagination,
                         per_page=per_page,
                         on_time_count=on_time_count,
                         late_count=late_count)

@bp.route('/home')
@login_required
def search():
    # Get search parameters from request
    search_params = {
        'title': request.args.get('title'),
        'nct_id': request.args.get('nct_id'),
        'organization': request.args.get('organization'),
        'status': request.args.get('status'),
        'date_type': request.args.get('date_type'),
        'date_from': request.args.get('date_from'),
        'date_to': request.args.get('date_to')
    }
    
    # If there are any search parameters, perform the search
    if any(search_params.values()) or request.args.getlist('compliance_status[]'):
        search_results = search_trials(search_params)
        pagination, per_page = paginate(search_results)
        
        # Convert to DataFrame for status counts
        df = pd.DataFrame(search_results)
        
        # Count statuses
        status_counts = df['status'].value_counts() if not df.empty else pd.Series()
        on_time_count = status_counts.get('Compliant', 0)
        late_count = status_counts.get('Incompliant', 0)
        
        return render_template('dashboards/home.html',
                            trials=pagination.items_page,
                            pagination=pagination,
                            per_page=per_page,
                            on_time_count=on_time_count,
                            late_count=late_count,
                            is_search=True)
    
    # If no search parameters, just show the search form
    return render_template('dashboards/home.html')

@bp.route('/organization/<org_ids>')
@login_required
def show_organization_dashboard(org_ids):
    # Convert org_ids to a tuple of integers
    org_ids = unquote(unquote(org_ids))
    org_list = tuple(int(id) for id in org_ids.split(',') if id)
    org_trials = get_org_trials(org_list)
    pagination, per_page = paginate(org_trials)
    
    # Convert to DataFrame
    df = pd.DataFrame(org_trials)

    # Count statuses
    status_counts = df['status'].value_counts() if not df.empty else pd.Series()
    on_time_count = status_counts.get('Compliant', 0)
    late_count = status_counts.get('Incompliant', 0)

    return render_template('dashboards/organization.html',
                         trials=pagination.items_page,
                         pagination=pagination,
                         per_page=per_page,
                         org_ids=org_ids,
                         on_time_count=on_time_count,
                         late_count=late_count)

@bp.route('/compare')
@login_required
def show_compare_organizations_dashboard():
    org_compliance = get_org_compliance()
    pagination, per_page = paginate(org_compliance)

    # Convert to DataFrame
    df = pd.DataFrame(org_compliance)

    # Count statuses
    on_time_count = df['on_time_count'].sum()
    late_count = df['late_count'].sum()
    total_organizations = df['name'].count()

    return render_template('dashboards/compare.html', 
        org_compliance=pagination.items_page,
        pagination=pagination,
        per_page=per_page,
        on_time_count=on_time_count,
        late_count=late_count,
        total_organizations=total_organizations
    )

@bp.route('/user/<int:user_id>')
@login_required
def show_user_dashboard(user_id):
    user_trials = get_user_trials(user_id)
    if user_trials:
        user_email = user_trials[0]['email']
        pagination, per_page = paginate(user_trials)

        # Convert to DataFrame
        df = pd.DataFrame(user_trials)

        # Count statuses
        status_counts = df['status'].value_counts() if not df.empty else pd.Series()
        on_time_count = status_counts.get('Compliant', 0)
        late_count = status_counts.get('Incompliant', 0)
        return render_template('dashboards/user.html', 
                            trials=pagination.items_page,
                            pagination=pagination,
                            per_page=per_page,
                            user_id=user_id,
                            user_email=user_email,
                            on_time_count=on_time_count,
                            late_count=late_count)
    else:
        user_email = current_user.get(user_id).email
        return render_template('dashboards/user.html',
                            trials=[],
                            pagination=None,
                            per_page=25,
                            user_id=user_id,
                            user_email=user_email)
