from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from .db import query
from .utils.pagination import paginate
import pandas as pd
from datetime import datetime

bp = Blueprint('dashboard', __name__)

def get_all_trials():
    sql = '''
    SELECT
        t.nct_id,
        t.title,
        o.name,
        u.email,
        tc.status,
        t.start_date,
        t.completion_date,
        t.reporting_due_date,
        tc.last_checked,
        o.id,
        t.user_id
    FROM trial t
    LEFT JOIN trial_compliance tc ON t.id = tc.trial_id
    LEFT JOIN organization o ON o.id = t.organization_id
    LEFT JOIN ctgov_user u ON u.id = t.user_id
    ORDER BY nct_id ASC
    '''
    return query(sql)

def get_org_trials(org_id):
    sql = '''
    SELECT 
        t.nct_id,
        t.title,
        o.name,
        u.email,
        tc.status,
        t.start_date,
        t.completion_date,
        t.reporting_due_date,
        tc.last_checked,
        t.user_id,
        o.id
    FROM trial t
    LEFT JOIN trial_compliance tc ON t.id = tc.trial_id
    LEFT JOIN organization o ON o.id = t.organization_id
    LEFT JOIN ctgov_user u ON u.id = t.user_id
    WHERE o.id = %s
    ORDER BY t.nct_id ASC
    '''
    return query(sql, [org_id])

def get_user_trials(user_id):
    sql = '''
    SELECT 
        t.nct_id,
        t.title,
        o.name,
        u.email,
        tc.status,
        t.start_date,
        t.completion_date,
        t.reporting_due_date,
        tc.last_checked,
        o.id
    FROM trial t
    LEFT JOIN trial_compliance tc ON t.id = tc.trial_id
    LEFT JOIN organization o ON o.id = t.organization_id
    LEFT JOIN ctgov_user u ON u.id = t.user_id
    WHERE u.id = %s
    ORDER BY t.nct_id ASC
    '''
    return query(sql, [user_id])

def search_trials(params):

    
    base_sql = '''
    SELECT DISTINCT
        t.nct_id,
        t.title,
        o.name,
        u.email,
        tc.status,
        t.start_date,
        t.completion_date,
        t.reporting_due_date,
        tc.last_checked,
        o.id,
        t.user_id
    FROM trial t
    LEFT JOIN trial_compliance tc ON t.id = tc.trial_id
    LEFT JOIN organization o ON o.id = t.organization_id
    LEFT JOIN ctgov_user u ON u.id = t.user_id
    WHERE 1=1
    '''
    
    conditions = []
    values = []
    
    if params.get('title'):
        conditions.append("t.title ILIKE %s")
        values.append(f"%{params['title']}%")
        
    if params.get('nct_id'):
        conditions.append("t.nct_id ILIKE %s")
        values.append(f"%{params['nct_id']}%")
        
    if params.get('organization'):
        conditions.append("o.name ILIKE %s")
        values.append(f"%{params['organization']}%")
        
    if params.get('status'):
        conditions.append("t.status = %s")
        values.append(params['status'])
    
    # Handle date range
    date_type = params.get('date_type', 'completion')
    date_from = params.get('date_from')
    date_to = params.get('date_to')
    
    if date_from:
        if date_type == 'completion':
            conditions.append("t.completion_date >= %s")
        elif date_type == 'start':
            conditions.append("t.start_date >= %s")
        elif date_type == 'due':
            conditions.append("t.reporting_due_date >= %s")
        values.append(date_from)
    
    if date_to:
        if date_type == 'completion':
            conditions.append("t.completion_date <= %s")
        elif date_type == 'start':
            conditions.append("t.start_date <= %s")
        elif date_type == 'due':
            conditions.append("t.reporting_due_date <= %s")
        values.append(date_to)
    
    # Handle compliance status
    compliance_status = request.args.getlist('compliance_status[]')
    if compliance_status:
        status_conditions = []
        for status in compliance_status:
            if status == 'compliant':
                status_conditions.append("tc.status = 'on time'")
            elif status == 'non-compliant':
                status_conditions.append("tc.status = 'late'")
            elif status == 'pending':
                status_conditions.append("tc.status IS NULL")
        if status_conditions:
            conditions.append(f"({' OR '.join(status_conditions)})")
    
    if conditions:
        base_sql += " AND " + " AND ".join(conditions)
    
    base_sql += " ORDER BY t.nct_id ASC"
    
    return query(base_sql, values)

def get_org_compliance():
    sql = '''
    SELECT 
        o.id,
        o.name,
        COUNT(t.id) AS total_trials,
        SUM(CASE WHEN tc.status = 'on time' THEN 1 ELSE 0 END) AS on_time_count,
        SUM(CASE WHEN tc.status = 'late' THEN 1 ELSE 0 END) AS late_count
    FROM organization o
    LEFT JOIN trial t ON o.id = t.organization_id
    LEFT JOIN trial_compliance tc ON t.id = tc.trial_id
    GROUP BY o.id, o.name
    ORDER BY o.name ASC
    '''
    return query(sql)


@bp.route('/')
@login_required
def index():
    trials = get_all_trials()
    pagination, per_page = paginate(trials)
    
    # Convert to DataFrame for status counts
    df = pd.DataFrame(trials)
    
    # Count statuses
    status_counts = df['status'].value_counts() if not df.empty else pd.Series()
    on_time_count = status_counts.get('on time', 0)
    late_count = status_counts.get('late', 0)
    
    return render_template('dashboards/home.html',
                         trials=pagination.items_page,
                         pagination=pagination,
                         per_page=per_page,
                         on_time_count=on_time_count,
                         late_count=late_count)

@bp.route('/search')
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
        on_time_count = status_counts.get('on time', 0)
        late_count = status_counts.get('late', 0)
        
        return render_template('dashboards/home.html',
                            trials=pagination.items_page,
                            pagination=pagination,
                            per_page=per_page,
                            on_time_count=on_time_count,
                            late_count=late_count,
                            is_search=True)
    
    # If no search parameters, just show the search form
    return render_template('dashboards/search.html')

@bp.route('/organization/<int:org_id>')
@login_required
def show_organization_dashboard(org_id):
    org_trials = get_org_trials(org_id)
    pagination, per_page = paginate(org_trials)
    org_name = org_trials[0]['name'] if org_trials else 'Unknown Organization'
    
    # Convert to DataFrame
    df = pd.DataFrame(org_trials)

    # Count statuses
    status_counts = df['status'].value_counts() if not df.empty else pd.Series()
    on_time_count = status_counts.get('on time', 0)
    late_count = status_counts.get('late', 0)

    return render_template('dashboards/organization.html',
                         trials=pagination.items_page,
                         pagination=pagination,
                         per_page=per_page,
                         org_id=org_id,
                         org_name=org_name,
                         on_time_count=on_time_count,
                         late_count=late_count)

@bp.route('/compare')
@login_required
def show_compare_organizations_dashboard():
    org_compliance = get_org_compliance()
    return render_template('dashboards/compare.html', org_compliance=org_compliance)

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
        on_time_count = status_counts.get('on time', 0)
        late_count = status_counts.get('late', 0)
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
        print(user_email)
        return render_template('dashboards/user.html',
                            trials=[],
                            pagination=None,
                            per_page=25,
                            user_id=user_id,
                            user_email=user_email)
