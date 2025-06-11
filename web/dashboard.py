from flask import Blueprint, render_template
from flask_login import login_required, current_user
from .db import query

bp = Blueprint('dashboard', __name__)


def get_user_trials():
    sql = '''
    SELECT 
        t.nct_id,
        t.title,
        o.name,
        tc.status,
        t.start_date,
        t.completion_date,
        t.reporting_due_date,
        tc.last_checked
    FROM trial t
    LEFT JOIN trial_compliance tc ON t.id = tc.trial_id
    LEFT JOIN organization o ON o.id = t.organization_id
    ORDER BY nct_id ASC
    '''
    return query(sql)

def get_aact_trials():
    sql = '''
    SELECT *
    FROM studies
    LIMIT 500
    '''
    return aact_query(sql)


def get_org_compliance():
    sql = '''
    SELECT o.name,
           ROUND(100.0 * SUM(CASE WHEN tc.status = 'on time' THEN 1 ELSE 0 END) / COUNT(*), 2) AS rate
    FROM organization o
    JOIN trial t ON o.id = t.organization_id
    JOIN trial_compliance tc ON t.id = tc.trial_id
    GROUP BY o.name
    ORDER BY o.name
    '''
    return query(sql)


@bp.route('/')
@login_required
def index():
    org_rates = get_org_compliance()
    if (current_user.is_organization):
        trials = get_user_trials()
        return render_template('org_dashboard.html', trials=trials, org_rates=org_rates)
    else:
        trials = get_user_trials()
        return render_template('user_dashboard.html', trials=trials, org_rates=org_rates)
