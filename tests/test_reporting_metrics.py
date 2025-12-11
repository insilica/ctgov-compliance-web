from decimal import Decimal

from web.utils.reporting_metrics import build_reporting_kpis


def test_build_reporting_kpis_with_values():
    row = {
        'total_trials': 20,
        'compliant_count': 12,
        'trials_with_issues_count': 5,
        'avg_reporting_delay_days': Decimal('4.25')
    }

    kpis = build_reporting_kpis(row)

    assert kpis['total_trials'] == 20
    assert kpis['compliant_trials'] == 12
    assert kpis['overall_compliance_rate'] == 60.0
    assert kpis['trials_with_issues_count'] == 5
    assert kpis['trials_with_issues_pct'] == 25.0
    assert kpis['avg_reporting_delay_days'] == 4.3
    assert kpis['has_data'] is True


def test_build_reporting_kpis_handles_missing_row():
    kpis = build_reporting_kpis(None)

    assert kpis['total_trials'] == 0
    assert kpis['overall_compliance_rate'] == 0.0
    assert kpis['trials_with_issues_count'] == 0
    assert kpis['avg_reporting_delay_days'] == 0.0
    assert kpis['has_data'] is False
