"""Utilities for shaping reporting KPI data for templates and client scripts."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Optional


def _coerce_number(value: Optional[Any], cast_type=float) -> float:
    """Convert database numeric values (including Decimal) into Python numbers."""
    if value is None:
        return cast_type(0)
    if isinstance(value, Decimal):
        return cast_type(value)
    if cast_type is int:
        try:
            return cast_type(round(value))
        except TypeError:
            return cast_type(0)
    try:
        return cast_type(value)
    except (TypeError, ValueError):
        return cast_type(0)


def _round_half_up(value: Any, places: int = 1) -> float:
    """Round using the conventional half-up strategy."""
    quant = Decimal('1').scaleb(-places)
    decimal_value = value if isinstance(value, Decimal) else Decimal(str(value or 0))
    return float(decimal_value.quantize(quant, rounding=ROUND_HALF_UP))


def build_reporting_kpis(row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize KPI query results into template-ready primitives."""
    row = row or {}
    total_trials = int(_coerce_number(row.get('total_trials'), int))
    compliant_trials = int(_coerce_number(row.get('compliant_count'), int))
    issues_count = int(_coerce_number(row.get('trials_with_issues_count'), int))
    avg_delay_days_raw = _coerce_number(row.get('avg_reporting_delay_days') or 0.0, float)

    overall_rate = (compliant_trials / total_trials * 100) if total_trials else 0.0
    issue_pct = (issues_count / total_trials * 100) if total_trials else 0.0

    return {
        'total_trials': total_trials,
        'compliant_trials': compliant_trials,
        'overall_compliance_rate': _round_half_up(overall_rate, 1),
        'trials_with_issues_count': issues_count,
        'trials_with_issues_pct': _round_half_up(issue_pct, 1),
        'avg_reporting_delay_days': _round_half_up(avg_delay_days_raw, 1),
        'has_data': total_trials > 0
    }
