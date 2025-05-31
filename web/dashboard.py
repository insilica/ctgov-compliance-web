from flask import Blueprint, render_template
from flask_login import login_required, current_user
from .db import query

bp = Blueprint('dashboard', __name__)


def get_user_trials(user_id):
    sql = '''
    SELECT t.nct_id, t.title, tc.status
    FROM trial t
    JOIN trial_compliance tc ON t.id = tc.trial_id
    JOIN user_organization uo ON t.organization_id = uo.organization_id
    WHERE uo.user_id = %s
    ORDER BY t.nct_id
    '''
    return query(sql, [user_id])


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
    trials = get_user_trials(current_user.id)
    org_rates = get_org_compliance()
    return render_template('dashboard.html', trials=trials, org_rates=org_rates)
