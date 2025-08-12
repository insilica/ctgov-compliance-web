from web.db import query
from flask import request


def get_all_trials_count():
    """Get total count of all trials"""
    sql = '''
    SELECT COUNT(*) FROM trial
    '''
    result = query(sql)
    return result[0]['count'] if result else 0


def get_all_trials(page=None, per_page=None, count_only=False):
    if count_only:
        select_columns = '''
        SUM(CASE WHEN tc.status = 'Compliant' THEN 1 ELSE 0 END) as compliant_count,
        SUM(CASE WHEN tc.status = 'Incompliant' THEN 1 ELSE 0 END) as incompliant_count,
        SUM(CASE WHEN tc.status IS NULL THEN 1 ELSE 0 END) as pending_count
        '''
        sql = f'''
            SELECT {select_columns}
            FROM trial t
            LEFT JOIN trial_compliance tc ON t.id = tc.trial_id
        '''
        return query(sql)
    else:
        select_columns = '''
        t.nct_id, t.title, o.name, u.email, tc.status,
        t.start_date, t.completion_date, t.reporting_due_date,
        tc.last_checked, o.id, t.user_id, o.created_at as org_created_at, uo.role as user_role
        '''
        sql = f'''
            SELECT {select_columns}
            FROM trial t
            LEFT JOIN trial_compliance tc ON t.id = tc.trial_id
            LEFT JOIN organization o ON o.id = t.organization_id
            LEFT JOIN ctgov_user u ON u.id = t.user_id
            LEFT JOIN user_organization uo ON u.id = uo.user_id AND o.id = uo.organization_id
            ORDER BY t.start_date DESC
        '''
        if page is not None and per_page is not None:
            offset = (page - 1) * per_page
            sql += f' LIMIT {per_page} OFFSET {offset}'
        return query(sql)


def get_org_trials_count(org_ids):
    """Get total count of trials for specific organizations"""
    sql = '''
    SELECT COUNT(*)
    FROM trial t
    LEFT JOIN trial_compliance tc ON t.id = tc.trial_id
    LEFT JOIN organization o ON o.id = t.organization_id
    LEFT JOIN ctgov_user u ON u.id = t.user_id
    LEFT JOIN user_organization uo ON u.id = uo.user_id AND o.id = uo.organization_id
    WHERE o.id IN %s
    '''
    result = query(sql, [org_ids])
    return result[0]['count'] if result else 0


def get_org_trials(org_ids, page=None, per_page=None):
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
        o.id,
        o.created_at as org_created_at,
        uo.role as user_role
    FROM trial t
    LEFT JOIN trial_compliance tc ON t.id = tc.trial_id
    LEFT JOIN organization o ON o.id = t.organization_id
    LEFT JOIN ctgov_user u ON u.id = t.user_id
    LEFT JOIN user_organization uo ON u.id = uo.user_id AND o.id = uo.organization_id
    WHERE o.id IN %s
    ORDER BY t.title ASC
    '''
    
    # Add LIMIT and OFFSET if pagination parameters are provided
    if page is not None and per_page is not None:
        offset = (page - 1) * per_page
        sql += f' LIMIT {per_page} OFFSET {offset}'
    
    return query(sql, [org_ids])


def get_user_trials_count(user_id):
    """Get total count of trials for a specific user"""
    sql = '''
    SELECT COUNT(*)
    FROM trial t
    LEFT JOIN trial_compliance tc ON t.id = tc.trial_id
    LEFT JOIN organization o ON o.id = t.organization_id
    LEFT JOIN ctgov_user u ON u.id = t.user_id
    LEFT JOIN user_organization uo ON u.id = uo.user_id AND o.id = uo.organization_id
    WHERE u.id = %s
    '''
    result = query(sql, [user_id])
    return result[0]['count'] if result else 0


def get_user_trials(user_id, page=None, per_page=None):
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
        o.id,
        o.created_at as org_created_at,
        uo.role as user_role
    FROM trial t
    LEFT JOIN trial_compliance tc ON t.id = tc.trial_id
    LEFT JOIN organization o ON o.id = t.organization_id
    LEFT JOIN ctgov_user u ON u.id = t.user_id
    LEFT JOIN user_organization uo ON u.id = uo.user_id AND o.id = uo.organization_id
    WHERE u.id = %s
    ORDER BY t.title ASC
    '''
    
    # Add LIMIT and OFFSET if pagination parameters are provided
    if page is not None and per_page is not None:
        offset = (page - 1) * per_page
        sql += f' LIMIT {per_page} OFFSET {offset}'
    
    return query(sql, [user_id])


def search_trials_count(params):
    """Get total count of search results"""
    base_sql = '''
    SELECT COUNT(DISTINCT t.id)
    FROM trial t
    LEFT JOIN trial_compliance tc ON t.id = tc.trial_id
    LEFT JOIN organization o ON o.id = t.organization_id
    LEFT JOIN ctgov_user u ON u.id = t.user_id
    LEFT JOIN user_organization uo ON u.id = uo.user_id AND o.id = uo.organization_id
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
    
    result = query(base_sql, values)
    return result[0]['count'] if result else 0


def search_trials(params, page=None, per_page=None, count_only=False):
    if count_only:
        select_columns = '''
        SUM(CASE WHEN tc.status = 'Compliant' THEN 1 ELSE 0 END) as compliant_count,
        SUM(CASE WHEN tc.status = 'Incompliant' THEN 1 ELSE 0 END) as incompliant_count,
        SUM(CASE WHEN tc.status IS NULL THEN 1 ELSE 0 END) as pending_count
        '''
        distinct_clause = ''
        order_by = ''
    else:
        select_columns = '''
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
        t.user_id,
        o.created_at as org_created_at,
        uo.role as user_role
        '''
        distinct_clause = 'DISTINCT'
        order_by = ' ORDER BY t.title ASC'

    base_sql = f'''
    SELECT {distinct_clause}
        {select_columns}
    FROM trial t
    LEFT JOIN trial_compliance tc ON t.id = tc.trial_id
    LEFT JOIN organization o ON o.id = t.organization_id
    LEFT JOIN ctgov_user u ON u.id = t.user_id
    LEFT JOIN user_organization uo ON u.id = uo.user_id AND o.id = uo.organization_id
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

    base_sql += order_by

    # Add LIMIT and OFFSET if pagination parameters are provided (but not for count queries)
    if not count_only and page is not None and per_page is not None:
        offset = (page - 1) * per_page
        base_sql += f' LIMIT {per_page} OFFSET {offset}'

    return query(base_sql, values)


def get_org_compliance_count(min_compliance=None, max_compliance=None, min_trials=None, max_trials=None):
    """Get total count of organizations matching compliance criteria"""
    sql = '''
    SELECT COUNT(*)
    FROM (
        SELECT 
            o.id,
            o.name,
            o.email_domain,
            o.created_at,
            COUNT(t.id) AS total_trials,
            SUM(CASE WHEN tc.status = 'Compliant' THEN 1 ELSE 0 END) AS on_time_count,
            SUM(CASE WHEN tc.status = 'Incompliant' THEN 1 ELSE 0 END) AS late_count,
            -- Calculate reporting rate as percentage of trials with status
            ROUND(
                (COUNT(CASE WHEN tc.status IS NOT NULL THEN 1 END) * 100.0 / NULLIF(COUNT(t.id), 0)), 
                1
            ) AS reporting_rate,
            -- Placeholder for funding source (would need additional table)
            NULL AS funding_source,
            -- Placeholder for Wilson LCB score (would need calculation)
            NULL AS wilson_lcb_score
        FROM organization o
        LEFT JOIN trial t ON o.id = t.organization_id
        LEFT JOIN trial_compliance tc ON t.id = tc.trial_id
        GROUP BY o.id, o.name, o.email_domain, o.created_at
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
    sql += '\n    ) AS subquery'
    
    result = query(sql, params)
    return result[0]['count'] if result else 0


def get_org_compliance(min_compliance=None, max_compliance=None, min_trials=None, max_trials=None, page=None, per_page=None):
    sql = '''
    SELECT 
        o.id,
        o.name,
        o.email_domain,
        o.created_at,
        COUNT(t.id) AS total_trials,
        SUM(CASE WHEN tc.status = 'Compliant' THEN 1 ELSE 0 END) AS on_time_count,
        SUM(CASE WHEN tc.status = 'Incompliant' THEN 1 ELSE 0 END) AS late_count,
        -- Calculate reporting rate as percentage of trials with status
        ROUND(
            (COUNT(CASE WHEN tc.status IS NOT NULL THEN 1 END) * 100.0 / NULLIF(COUNT(t.id), 0)), 
            1
        ) AS reporting_rate,
        -- Placeholder for funding source (would need additional table)
        NULL AS funding_source,
        -- Placeholder for Wilson LCB score (would need calculation)
        NULL AS wilson_lcb_score
    FROM organization o
    LEFT JOIN trial t ON o.id = t.organization_id
    LEFT JOIN trial_compliance tc ON t.id = tc.trial_id
    GROUP BY o.id, o.name, o.email_domain, o.created_at
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
    sql += '\nORDER BY total_trials DESC, o.name ASC'
    
    # Add LIMIT and OFFSET if pagination parameters are provided
    if page is not None and per_page is not None:
        offset = (page - 1) * per_page
        sql += f' LIMIT {per_page} OFFSET {offset}'
    
    return query(sql, params)


def get_enhanced_trial_analytics(search_params=None, compliance_status_list=None):
    """Get enhanced trial analytics including compliance metrics, overdue days, etc."""
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
        t.user_id,
        -- Calculate days overdue (negative means not due yet)
        CASE 
            WHEN tc.status = 'Incompliant' AND t.reporting_due_date < CURRENT_DATE 
            THEN CURRENT_DATE - t.reporting_due_date
            ELSE 0
        END as days_overdue,
        -- Calculate time to next deadline
        CASE 
            WHEN t.reporting_due_date >= CURRENT_DATE 
            THEN t.reporting_due_date - CURRENT_DATE
            ELSE 0
        END as days_until_due,
        -- Risk score based on compliance history and timeline
        CASE 
            WHEN tc.status = 'Incompliant' AND t.reporting_due_date < CURRENT_DATE THEN 'High'
            WHEN tc.status IS NULL AND t.reporting_due_date <= CURRENT_DATE + INTERVAL '30 days' THEN 'Medium'
            WHEN tc.status IS NULL AND t.reporting_due_date <= CURRENT_DATE + INTERVAL '60 days' THEN 'Low'
            ELSE 'Normal'
        END as risk_level,
        -- Trial duration for analysis
        t.completion_date - t.start_date as trial_duration_days
    FROM trial t
    LEFT JOIN trial_compliance tc ON t.id = tc.trial_id
    LEFT JOIN organization o ON o.id = t.organization_id
    LEFT JOIN ctgov_user u ON u.id = t.user_id
    WHERE 1=1
    '''
    
    conditions = []
    values = []
    
    if search_params:
        if search_params.get('title'):
            conditions.append("t.title ILIKE %s")
            values.append(f"%{search_params['title']}%")
            
        if search_params.get('nct_id'):
            conditions.append("t.nct_id ILIKE %s")
            values.append(f"%{search_params['nct_id']}%")
            
        if search_params.get('organization'):
            conditions.append("o.name ILIKE %s")
            values.append(f"%{search_params['organization']}%")
        
        if search_params.get('user_email'):
            conditions.append("u.email ILIKE %s")
            values.append(f"%{search_params['user_email']}%")
        
        # Handle date range
        date_type = search_params.get('date_type', 'completion')
        date_from = search_params.get('date_from')
        date_to = search_params.get('date_to')
        
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
    if compliance_status_list:
        status_conditions = []
        for status in compliance_status_list:
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
    
    base_sql += " ORDER BY days_overdue DESC, t.reporting_due_date ASC"
    
    return query(base_sql, values)


def get_compliance_summary_stats(search_params=None, compliance_status_list=None):
    """Get comprehensive compliance summary statistics."""
    # Use the enhanced analytics function to get detailed data
    trials = get_enhanced_trial_analytics(search_params, compliance_status_list)
    
    if not trials:
        return {
            'total_trials': 0,
            'compliant_count': 0,
            'incompliant_count': 0,
            'pending_count': 0,
            'compliance_rate': 0,
            'avg_days_overdue': 0,
            'high_risk_count': 0,
            'medium_risk_count': 0,
            'low_risk_count': 0,
            'trials_due_soon': 0,
            'overdue_trials': 0
        }
    
    # Calculate summary statistics
    total_trials = len(trials)
    compliant_count = sum(1 for t in trials if t.get('status') == 'Compliant')
    incompliant_count = sum(1 for t in trials if t.get('status') == 'Incompliant')
    pending_count = sum(1 for t in trials if t.get('status') is None)
    
    compliance_rate = (compliant_count / total_trials * 100) if total_trials > 0 else 0
    
    # Calculate risk metrics
    high_risk_count = sum(1 for t in trials if t.get('risk_level') == 'High')
    medium_risk_count = sum(1 for t in trials if t.get('risk_level') == 'Medium')
    low_risk_count = sum(1 for t in trials if t.get('risk_level') == 'Low')
    
    # Calculate overdue metrics
    overdue_trials = sum(1 for t in trials if t.get('days_overdue', 0) > 0)
    trials_due_soon = sum(1 for t in trials if 0 < t.get('days_until_due', 0) <= 30)
    
    # Calculate average days overdue (only for overdue trials)
    overdue_days = [t.get('days_overdue', 0) for t in trials if t.get('days_overdue', 0) > 0]
    avg_days_overdue = sum(overdue_days) / len(overdue_days) if overdue_days else 0
    
    return {
        'total_trials': total_trials,
        'compliant_count': compliant_count,
        'incompliant_count': incompliant_count,
        'pending_count': pending_count,
        'compliance_rate': round(compliance_rate, 1),
        'avg_days_overdue': round(avg_days_overdue, 1),
        'high_risk_count': high_risk_count,
        'medium_risk_count': medium_risk_count,
        'low_risk_count': low_risk_count,
        'trials_due_soon': trials_due_soon,
        'overdue_trials': overdue_trials
    }


def get_critical_issues(search_params=None, compliance_status_list=None):
    """Get critical issues requiring immediate attention."""
    trials = get_enhanced_trial_analytics(search_params, compliance_status_list)
    
    critical_issues = []
    
    for trial in trials:
        # Severely overdue trials (>30 days)
        if trial.get('days_overdue', 0) > 30:
            critical_issues.append({
                'type': 'Severely Overdue',
                'priority': 'Critical',
                'trial_id': trial.get('nct_id'),
                'title': trial.get('title'),
                'organization': trial.get('name'),
                'days_overdue': trial.get('days_overdue'),
                'description': f"Trial {trial.get('nct_id')} is {trial.get('days_overdue')} days overdue for compliance reporting"
            })
        
        # Trials due very soon (within 7 days)
        elif 0 < trial.get('days_until_due', 0) <= 7:
            critical_issues.append({
                'type': 'Due Soon',
                'priority': 'High',
                'trial_id': trial.get('nct_id'),
                'title': trial.get('title'),
                'organization': trial.get('name'),
                'days_until_due': trial.get('days_until_due'),
                'description': f"Trial {trial.get('nct_id')} compliance reporting due in {trial.get('days_until_due')} days"
            })
        
        # High risk trials with no compliance status
        elif trial.get('risk_level') == 'High' and trial.get('status') is None:
            critical_issues.append({
                'type': 'High Risk - No Status',
                'priority': 'High',
                'trial_id': trial.get('nct_id'),
                'title': trial.get('title'),
                'organization': trial.get('name'),
                'description': f"High-risk trial {trial.get('nct_id')} has no compliance status recorded"
            })
    
    # Sort by priority: Critical first, then High
    priority_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3}
    critical_issues.sort(key=lambda x: priority_order.get(x['priority'], 3))
    
    return critical_issues


def get_organization_risk_analysis(min_compliance=None, max_compliance=None, min_trials=None, max_trials=None):
    """Get enhanced organization compliance with risk analysis."""
    sql = '''
    SELECT 
        o.id,
        o.name,
        COUNT(t.id) AS total_trials,
        SUM(CASE WHEN tc.status = 'Compliant' THEN 1 ELSE 0 END) AS on_time_count,
        SUM(CASE WHEN tc.status = 'Incompliant' THEN 1 ELSE 0 END) AS late_count,
        SUM(CASE WHEN tc.status IS NULL THEN 1 ELSE 0 END) AS pending_count,
        -- Calculate overdue metrics
        SUM(CASE 
            WHEN tc.status = 'Incompliant' AND t.reporting_due_date < CURRENT_DATE 
            THEN CURRENT_DATE - t.reporting_due_date
            ELSE 0
        END) AS total_overdue_days,
        -- Count high-risk trials
        SUM(CASE 
            WHEN tc.status = 'Incompliant' AND t.reporting_due_date < CURRENT_DATE 
            THEN 1 ELSE 0
        END) AS high_risk_trials,
        -- Average trial duration
        AVG(t.completion_date - t.start_date) AS avg_trial_duration,
        -- Most recent compliance check
        MAX(tc.last_checked) AS last_compliance_check
    FROM organization o
    LEFT JOIN trial t ON o.id = t.organization_id
    LEFT JOIN trial_compliance tc ON t.id = tc.trial_id
    GROUP BY o.id, o.name
    '''
    
    having_clauses = []
    params = []
    
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
    
    sql += '\nORDER BY (SUM(CASE WHEN tc.status = \'Compliant\' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(t.id),0)) ASC'
    
    return query(sql, params)
