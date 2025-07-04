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
    ORDER BY t.title ASC
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
    ORDER BY t.title ASC
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
        t.user_id,
        o.id
    FROM trial t
    LEFT JOIN trial_compliance tc ON t.id = tc.trial_id
    LEFT JOIN organization o ON o.id = t.organization_id
    LEFT JOIN ctgov_user u ON u.id = t.user_id
    WHERE u.id = %s
    ORDER BY t.title ASC
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
    
    if params.get('user_email'):
        conditions.append("u.email ILIKE %s")
        values.append(f"%{params['user_email']}%")
    
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
                status_conditions.append("tc.status = 'Compliant'")
            elif status == 'incompliant':
                status_conditions.append("tc.status = 'Incompliant'")
            elif status == 'pending':
                status_conditions.append("tc.status IS NULL")
        if status_conditions:
            conditions.append(f"({' OR '.join(status_conditions)})")
    
    if conditions:
        base_sql += " AND " + " AND ".join(conditions)
    
    base_sql += " ORDER BY t.title ASC"
    
    return query(base_sql, values)

def get_org_compliance(min_compliance=None, max_compliance=None, min_trials=None, max_trials=None):
    sql = '''
    SELECT 
        o.id,
        o.name,
        COUNT(t.id) AS total_trials,
        SUM(CASE WHEN tc.status = 'Compliant' THEN 1 ELSE 0 END) AS on_time_count,
        SUM(CASE WHEN tc.status = 'Incompliant' THEN 1 ELSE 0 END) AS late_count
    FROM organization o
    LEFT JOIN trial t ON o.id = t.organization_id
    LEFT JOIN trial_compliance tc ON t.id = tc.trial_id
    GROUP BY o.id, o.name
    '''
    having_clauses = []
    params = []
    # Compliance rate is calculated as (on_time_count / total_trials) * 100
    if min_compliance is not None:
        having_clauses.append('(SUM(CASE WHEN tc.status = \'Compliant\' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(t.id),0)) >= %s')
        params.append(min_compliance)
    if max_compliance is not None:
        having_clauses.append('(SUM(CASE WHEN tc.status = \'Compliant\' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(t.id),0)) <= %s')
        params.append(max_compliance)
    if min_trials is not None:
        having_clauses.append('COUNT(t.id) >= %s')
        params.append(min_trials)
    if max_trials is not None:
        having_clauses.append('COUNT(t.id) <= %s')
        params.append(max_trials)
    if having_clauses:
        sql += ' HAVING ' + ' AND '.join(having_clauses)
    sql += '\nORDER BY o.name ASC'
    return query(sql, params)
