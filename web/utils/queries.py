from web.db import query
from flask import request


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

def get_org_trials(org_ids):
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
    WHERE o.id IN %s
    ORDER BY t.nct_id ASC
    '''
    return query(sql, [org_ids])

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
