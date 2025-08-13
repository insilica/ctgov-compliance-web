from web.db import query
from flask import request
from opentelemetry import trace
# Cache imports with compatibility fallback
from functools import cached_property
tracer = trace.get_tracer(__name__)

class QueryManager:
    """A class to manage all database queries for the CTGov compliance application."""
    
    def __init__(self):
        """Initialize the QueryManager."""
        pass
    
    # ============================================================================
    # COMPLIANCE RATE QUERIES
    # ============================================================================
    
    @tracer.start_as_current_span("queries.get_compliance_rate")
    def get_compliance_rate(self, filter=None, params=None):
        current_span = trace.get_current_span()
        if filter: current_span.set_attribute("filter", filter)
        if params: current_span.set_attribute("params", params)
            
        sql = '''
            SELECT
                COUNT(trial_id) FILTER (WHERE compliance_status = 'Compliant') AS compliant_count,
                COUNT(trial_id) FILTER (WHERE compliance_status = 'Incompliant') AS incompliant_count
            FROM joined_trials
        '''
        if filter:
            sql += f"WHERE {filter}"
            current_span.set_attribute("sql", sql)
            current_span.set_attribute("[params]", [params])
            return query(sql, [params])
        current_span.set_attribute("sql", sql)
        return query(sql)

    @tracer.start_as_current_span("queries.get_compliance_rate_compare")
    def get_compliance_rate_compare(self, min_compliance=None, max_compliance=None, min_trials=None, max_trials=None):
        current_span = trace.get_current_span()
        if min_compliance: current_span.set_attribute("min_compliance", min_compliance)
        if max_compliance: current_span.set_attribute("max_compliance", max_compliance)
        if min_trials: current_span.set_attribute("min_trials", min_trials)
        if max_trials: current_span.set_attribute("max_trials", max_trials)

        sql = '''
                SELECT
                    SUM(on_time_count) AS compliant_count,
                    SUM(late_count) AS incompliant_count
                FROM compare_orgs
            '''
        where_clauses = []
        params = []
        # Compliance rate is calculated as (on_time_count / total_trials) * 100
        if min_compliance is not None:
            where_clauses.append('(on_time_count * 100.0 / NULLIF(total_trials,0)) >= %s')
            params.append(min_compliance)
        if max_compliance is not None:
            where_clauses.append('(on_time_count * 100.0 / NULLIF(total_trials,0)) <= %s')
            params.append(max_compliance)
        if min_trials is not None:
            where_clauses.append('total_trials >= %s')
            params.append(min_trials)
        if max_trials is not None:
            where_clauses.append('total_trials <= %s')
            params.append(max_trials)
        if where_clauses:
            sql += ' WHERE ' + ' AND '.join(where_clauses)
        current_span.set_attribute("sql", sql)
        current_span.set_attribute("params", params)
        return query(sql, params)
    
    # ============================================================================
    # TRIAL RETRIEVAL QUERIES
    # ============================================================================
    
    @tracer.start_as_current_span("queries.get_all_trials")
    def get_all_trials(self, page=None, per_page=None, count='*'):
        current_span = trace.get_current_span()
        if page: current_span.set_attribute("page", page)
        if per_page: current_span.set_attribute("per_page", per_page)
        current_span.set_attribute("count", count)

        sql = f'''
            SELECT {count} FROM joined_trials
        '''

        if page is not None and per_page is not None:
            offset = (page - 1) * per_page
            sql += f' LIMIT {per_page} OFFSET {offset}'
        current_span.set_attribute("sql", sql)
        return query(sql)

    @tracer.start_as_current_span("queries.get_org_trials")
    def get_org_trials(self, org_ids, page=None, per_page=None, count='*'):
        current_span = trace.get_current_span()
        current_span.set_attribute("org_ids", org_ids)
        if page: current_span.set_attribute("page", page)
        if per_page: current_span.set_attribute("per_page", per_page)
        current_span.set_attribute("count", count)
        
        sql = f'''
            SELECT {count} FROM joined_trials
            WHERE organization_id IN %s
        '''
        
        # Add LIMIT and OFFSET if pagination parameters are provided
        if page is not None and per_page is not None:
            offset = (page - 1) * per_page
            sql += f' LIMIT {per_page} OFFSET {offset}'
        current_span.set_attribute("sql", sql)
        current_span.set_attribute("[tuple(org_ids)]", [tuple(org_ids)])
        return query(sql, [tuple(org_ids)])


    @tracer.start_as_current_span("queries.get_user_trials")
    def get_user_trials(self, user_id, page=None, per_page=None, count='*'):
        current_span = trace.get_current_span()
        current_span.set_attribute("user_id", user_id)
        if page: current_span.set_attribute("page", page)
        if per_page: current_span.set_attribute("per_page", per_page)
        current_span.set_attribute("count", count)
        
        sql = f'''
            SELECT {count} FROM joined_trials
            WHERE user_id = %s
        '''
        
        # Add LIMIT and OFFSET if pagination parameters are provided
        if page is not None and per_page is not None:
            offset = (page - 1) * per_page
            sql += f' LIMIT {per_page} OFFSET {offset}'
        current_span.set_attribute("sql", sql)
        current_span.set_attribute("[user_id]", [user_id])
        return query(sql, [user_id])
    
    # ============================================================================
    # SEARCH QUERIES
    # ============================================================================

    @tracer.start_as_current_span("queries.search_trials")
    def search_trials(self, params, page=None, per_page=None, count='*'):
        current_span = trace.get_current_span()
        current_span.set_attribute("params", params)
        if page: current_span.set_attribute("page", page)
        if per_page: current_span.set_attribute("per_page", per_page)
        current_span.set_attribute("count", count)
        
        base_sql = f'''
            SELECT {count}
            FROM joined_trials
        '''
        
        conditions = []
        values = []
        
        if params.get('title'):
            conditions.append("title ILIKE %s")
            values.append(f"%{params['title']}%")
            
        if params.get('nct_id'):
            conditions.append("nct_id ILIKE %s")
            values.append(f"%{params['nct_id']}%")
            
        if params.get('organization'):
            conditions.append("organization_name ILIKE %s")
            values.append(f"%{params['organization']}%")
            
        if params.get('status'):
            conditions.append("status = %s")
            values.append(params['status'])
        
        if params.get('user_email'):
            conditions.append("user_email ILIKE %s")
            values.append(f"%{params['user_email']}%")
        
        # Handle date range
        date_type = params.get('date_type', 'completion')
        date_from = params.get('date_from')
        date_to = params.get('date_to')
        
        if date_from:
            if date_type == 'completion':
                conditions.append("completion_date >= %s")
            elif date_type == 'start':
                conditions.append("start_date >= %s")
            elif date_type == 'due':
                conditions.append("reporting_due_date >= %s")
            values.append(date_from)
        
        if date_to:
            if date_type == 'completion':
                conditions.append("completion_date <= %s")
            elif date_type == 'start':
                conditions.append("start_date <= %s")
            elif date_type == 'due':
                conditions.append("reporting_due_date <= %s")
            values.append(date_to)
        
        # Handle compliance status
        compliance_status = params['compliance_status']
        if compliance_status:
            status_conditions = []
            for status in compliance_status:
                if status == 'compliant':
                    status_conditions.append("compliance_status = 'Compliant'")
                elif status == 'incompliant':
                    status_conditions.append("compliance_status = 'Incompliant'")
                elif status == 'pending':
                    status_conditions.append("compliance_status IS NULL")
            if status_conditions:
                conditions.append(f"({' OR '.join(status_conditions)})")

        if conditions:
            base_sql += " WHERE " + " AND ".join(conditions)

        # Add LIMIT and OFFSET if pagination parameters are provided (but not for count queries)
        if page is not None and per_page is not None:
            offset = (page - 1) * per_page
            base_sql += f' LIMIT {per_page} OFFSET {offset}'

        current_span.set_attribute("sql", base_sql)
        print(base_sql)
        current_span.set_attribute("values", values)
        return query(base_sql, values)
    
    # ============================================================================
    # ORGANIZATION COMPLIANCE QUERIES
    # ============================================================================

    @tracer.start_as_current_span("queries.get_org_compliance")
    def get_org_compliance(self, min_compliance=None, max_compliance=None, min_trials=None, max_trials=None, page=None, per_page=None, count='*'):
        current_span = trace.get_current_span()
        if min_compliance: current_span.set_attribute("min_compliance", min_compliance)
        if max_compliance: current_span.set_attribute("max_compliance", max_compliance)
        if min_trials: current_span.set_attribute("min_trials", min_trials)
        if max_trials: current_span.set_attribute("max_trials", max_trials)
        if page: current_span.set_attribute("page", page)
        if per_page: current_span.set_attribute("per_page", per_page)
        current_span.set_attribute("count", count)

        sql = f'''
            SELECT 
                {count}
            FROM compare_orgs
        '''

        where_clauses = []
        params = []
        # Compliance rate is calculated as (on_time_count / total_trials) * 100
        if min_compliance is not None:
            where_clauses.append('(on_time_count * 100.0 / NULLIF(total_trials,0)) >= %s')
            params.append(min_compliance)
        if max_compliance is not None:
            where_clauses.append('(on_time_count * 100.0 / NULLIF(total_trials,0)) <= %s')
            params.append(max_compliance)
        if min_trials is not None:
            where_clauses.append('total_trials >= %s')
            params.append(min_trials)
        if max_trials is not None:
            where_clauses.append('total_trials <= %s')
            params.append(max_trials)
        if where_clauses:
            sql += ' WHERE ' + ' AND '.join(where_clauses)
        
        # Add LIMIT and OFFSET if pagination parameters are provided
        if page is not None and per_page is not None:
            offset = (page - 1) * per_page
            sql += f' LIMIT {per_page} OFFSET {offset}'
        
        current_span.set_attribute("sql", sql)
        current_span.set_attribute("params", params)
        return query(sql, params)
    
    # ============================================================================
    # ANALYTICS AND REPORTING QUERIES
    # ============================================================================
    
    @tracer.start_as_current_span("queries.get_enhanced_trial_analytics")
    def get_enhanced_trial_analytics(self, search_params=None, compliance_status_list=None):
        current_span = trace.get_current_span()
        if search_params: current_span.set_attribute("search_params", search_params)
        if compliance_status_list: current_span.set_attribute("compliance_status_list", compliance_status_list)
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
        
        current_span.set_attribute("sql", base_sql)
        current_span.set_attribute("values", values)
        return query(base_sql, values)

    @tracer.start_as_current_span("queries.get_compliance_summary_stats")
    def get_compliance_summary_stats(self, search_params=None, compliance_status_list=None):
        """Get comprehensive compliance summary statistics."""
        current_span = trace.get_current_span()
        if search_params: current_span.set_attribute("search_params", search_params)
        if compliance_status_list: current_span.set_attribute("compliance_status_list", compliance_status_list)
        trials = self.get_enhanced_trial_analytics(search_params, compliance_status_list)
        
        if not trials:
            current_span.set_attribute('summary', summary)
            summary = {
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
            return summary
        
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
        
        summary = {
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

        current_span.set_attribute('summary', summary)
        return summary

    def get_critical_issues(self, search_params=None, compliance_status_list=None):
        """Get critical issues requiring immediate attention."""
        trials = self.get_enhanced_trial_analytics(search_params, compliance_status_list)
        
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

    def get_organization_risk_analysis(self, min_compliance=None, max_compliance=None, min_trials=None, max_trials=None):
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