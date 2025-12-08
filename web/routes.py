import csv
import io
import json
import os
from datetime import datetime
from textwrap import dedent
from threading import Lock

from flask import Blueprint, render_template, stream_template, request, jsonify, make_response, current_app
from flask_login import login_required, current_user    # pragma: no cover, current_user
from .utils.route_helpers import (
    process_index_request,
    process_search_request,
    process_organization_dashboard_request,
    process_compare_organizations_request,
    process_user_dashboard_request,
    process_reporting_request,
    build_action_items_export_rows,
)
from .utils.queries import (
    QueryManager,
)
from .mcp.ctgov_mcp import ClinicalTrialsMCPServer, UnifiedQueryInterface
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

bp = Blueprint('routes', __name__)
qm = QueryManager()

def _env_truthy(value: str, default: bool = True) -> bool:
    if value is None:
        return default
    return value.lower() not in ('0', 'false', 'no', 'off')

DEFAULT_USE_LLM = _env_truthy(os.getenv('USE_LLM_PARSER'), True)
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

README_FEATURES = [
    {
        "title": "Natural language understanding",
        "description": "Turns free-form compliance questions into ClinicalTrials.gov parameters with either Claude-powered or deterministic parsing."
    },
    {
        "title": "Automatic fallbacks",
        "description": "Uses the pattern parser whenever an LLM key is not configured so analysts can continue working."
    },
    {
        "title": "Comprehensive filtering",
        "description": "Supports every major ClinicalTrials.gov filter including phase, geography, regulatory posture, and publication requirements."
    },
    {
        "title": "Conversation memory",
        "description": "Keeps track of clarifying answers so multi-turn sessions stay grounded in prior constraints."
    },
    {
        "title": "MCP compatible",
        "description": "Ships with a ready-to-register MCP tool definition for orchestrators and agent frameworks."
    },
    {
        "title": "ACT awareness",
        "description": "Detects Applicable Clinical Trial scenarios and applies the right compliance rules automatically."
    },
]

PARAMETER_SECTIONS = [
    {
        "title": "Study filters",
        "items": [
            {"label": "study_type", "description": "Interventional | Observational | Expanded Access"},
            {"label": "status", "description": "com, rec, act, not, sus, ter, wit, unk"},
            {"label": "phase", "description": "PHASE1 | PHASE2 | PHASE3 | PHASE4 | EARLY_PHASE1"},
            {"label": "exclude_phase", "description": "Treat supplied phase list as exclusions"},
        ],
    },
    {
        "title": "Output controls",
        "items": [
            {"label": "has_results", "description": "Require posted results"},
            {"label": "has_publications", "description": "Require linked publications"},
            {"label": "fda_drug", "description": "Filter for FDA regulated drugs"},
            {"label": "fda_device", "description": "Filter for FDA regulated devices"},
        ],
    },
    {
        "title": "Location scope",
        "items": [
            {"label": "country", "description": "Country filter, e.g., United States"},
            {"label": "state", "description": "State-level targeting"},
            {"label": "city", "description": "City-level targeting"},
        ],
    },
    {
        "title": "Date ranges",
        "items": [
            {"label": "start_date_min / max", "description": "Start date bounds"},
            {"label": "completion_date_min / max", "description": "Completion date bounds"},
        ],
    },
    {
        "title": "Search terms",
        "items": [
            {"label": "condition", "description": "Disease or condition focus"},
            {"label": "intervention", "description": "Treatment or therapy"},
            {"label": "sponsor", "description": "Lead organization"},
            {"label": "keywords", "description": "General keywords"},
        ],
    },
]

QUICK_START_SNIPPETS = [
    {
        "title": "MCP server usage",
        "language": "python",
        "code": dedent("""\
            from ctgov_mcp import ClinicalTrialsMCPServer

            server = ClinicalTrialsMCPServer()
            print(server.query("How many interventional trials have results?"))

            result = server.query_structured(
                study_type="Interventional",
                has_results=True,
                country="United States"
            )
            print(result)
        """),
    },
    {
        "title": "Direct API helpers",
        "language": "python",
        "code": dedent("""\
            from ctgov_mcp import mcp_query_trials, mcp_structured_query

            summary = mcp_query_trials("Show me ACT trials")
            print(summary)

            structured = mcp_structured_query(
                condition="diabetes",
                has_results=True,
                has_publications=True
            )
            print(structured)
        """),
    },
]

INTEGRATION_SNIPPETS = [
    {
        "title": "Flask endpoint (Integration Guide)",
        "language": "python",
        "description": "Expose a natural language endpoint that keeps a single ClinicalTrialsMCPServer warm.",
        "code": dedent("""\
            from flask import Flask, request, jsonify
            from ctgov_mcp import ClinicalTrialsMCPServer

            app = Flask(__name__)
            server = ClinicalTrialsMCPServer()

            @app.post("/api/clinical-trials/query")
            def query_trials():
                payload = request.get_json(force=True)
                result = server.query(payload.get("query", ""))
                return jsonify({"success": True, "result": result})
        """),
    },
    {
        "title": "Frontend service call",
        "language": "typescript",
        "description": "Call the backend endpoint from a React service using fetch.",
        "code": dedent("""\
            export async function queryClinicalTrials(query: string) {
              const response = await fetch("/api/clinical-trials/query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query })
              });
              if (!response.ok) {
                throw new Error("Query failed");
              }
              return response.json();
            }
        """),
    },
]

SAMPLE_PROMPTS = [
    "How many interventional trials have results?",
    "Show me ACT trials",
    "Completed United States trials without results",
]

WELCOME_MESSAGE = ""

README_SOURCE = "web/mcp/ctgov_mcp/README.md"
INTEGRATION_SOURCE = "web/mcp/ctgov_mcp/INTEGRATION_GUIDE.md"

mcp_server = ClinicalTrialsMCPServer(use_llm=DEFAULT_USE_LLM)
_workspace_sessions = {}
_workspace_lock = Lock()


def _sanitize_message(text):
    if not text:
        return ""
    replacements = {
        "✅": "Success:",
        "❌": "Error:",
        "✗": "Error:",
        "✓": "Success:",
    }
    for symbol, replacement in replacements.items():
        text = text.replace(symbol, replacement)
    return text.strip()


def _coerce_bool(value, default=None):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() not in ('0', 'false', 'no', 'off')
    return bool(value)


def _ensure_workspace_session(user_id, prefer_llm=None):
    target_mode = DEFAULT_USE_LLM if prefer_llm is None else prefer_llm
    with _workspace_lock:
        session_entry = _workspace_sessions.get(user_id)
        needs_new = session_entry is None
        if session_entry and prefer_llm is not None:
            needs_new = session_entry["interface"].use_llm != target_mode

        if needs_new:
            interface = UnifiedQueryInterface(use_llm=target_mode, api_key=ANTHROPIC_API_KEY)
            session_entry = {"interface": interface}
            _workspace_sessions[user_id] = session_entry

        return session_entry


def _reset_workspace_session(user_id, prefer_llm=None):
    target_mode = DEFAULT_USE_LLM if prefer_llm is None else prefer_llm
    with _workspace_lock:
        session_entry = _workspace_sessions.get(user_id)
        recreate = session_entry is None or session_entry["interface"].use_llm != target_mode
        if recreate:
            interface = UnifiedQueryInterface(use_llm=target_mode, api_key=ANTHROPIC_API_KEY)
            session_entry = {"interface": interface}
            _workspace_sessions[user_id] = session_entry
        else:
            session_entry["interface"].reset()
        return session_entry


@bp.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200

# Autocomplete API endpoints
@bp.route('/api/autocomplete/titles')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.autocomplete_titles")
def autocomplete_titles():
    """API endpoint for trial title autocomplete suggestions"""
    current_span = trace.get_current_span()
    query = request.args.get('q', '').strip()
    current_span.set_attribute("query.length", len(query))
    if len(query) < 2:
        return jsonify([])
    
    from .db import query as db_query
    sql = '''
        SELECT DISTINCT t.title
        FROM trial t
        WHERE t.title ILIKE %s
        ORDER BY t.title ASC
        LIMIT 10
        '''
    results = db_query(sql, [f"%{query}%"])
    suggestions = [row['title'] for row in results if row['title']]
    current_span.set_attribute("results.count", len(suggestions))
    return jsonify(suggestions)

@bp.route('/api/autocomplete/organizations')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.autocomplete_organizations")
def autocomplete_organizations():
    """API endpoint for organization name autocomplete suggestions"""
    current_span = trace.get_current_span()
    query = request.args.get('q', '').strip()
    current_span.set_attribute("query.length", len(query))
    if len(query) < 2:
        return jsonify([])
    
    from .db import query as db_query
    sql = '''
        SELECT DISTINCT o.name
        FROM organization o
        WHERE o.name ILIKE %s
        ORDER BY o.name ASC
        LIMIT 10
        '''
    results = db_query(sql, [f"%{query}%"])
    suggestions = [row['name'] for row in results if row['name']]
    current_span.set_attribute("results.count", len(suggestions))
    return jsonify(suggestions)

@bp.route('/api/autocomplete/nct_ids')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.autocomplete_nct_ids")
def autocomplete_nct_ids():
    """API endpoint for NCT ID autocomplete suggestions"""
    current_span = trace.get_current_span()
    query = request.args.get('q', '').strip()
    current_span.set_attribute("query.length", len(query))
    if len(query) < 3:
        return jsonify([])
    
    from .db import query as db_query
    sql = '''
        SELECT DISTINCT t.nct_id
        FROM trial t
        WHERE t.nct_id ILIKE %s
        ORDER BY t.nct_id ASC
        LIMIT 10
        '''
    results = db_query(sql, [f"%{query}%"])
    suggestions = [row['nct_id'] for row in results if row['nct_id']]
    current_span.set_attribute("results.count", len(suggestions))
    return jsonify(suggestions)

@bp.route('/api/autocomplete/user_emails')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.autocomplete_user_emails")
def autocomplete_user_emails():
    """API endpoint for user email autocomplete suggestions"""
    current_span = trace.get_current_span()
    query = request.args.get('q', '').strip()
    current_span.set_attribute("query.length", len(query))
    if len(query) < 2:
        return jsonify([])
    
    from .db import query as db_query
    sql = '''
        SELECT DISTINCT u.email
        FROM ctgov_user u
        WHERE u.email ILIKE %s
        ORDER BY u.email ASC
        LIMIT 10
        '''
    results = db_query(sql, [f"%{query}%"])
    suggestions = [row['email'] for row in results if row['email']]
    current_span.set_attribute("results.count", len(suggestions))
    return jsonify(suggestions)

@bp.route('/')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.index")
def index():
    current_span = trace.get_current_span()
    search_params = {
        'title': request.args.get('title'),
        'nct_id': request.args.get('nct_id'),
        'organization': request.args.get('organization'),
        'user_email': request.args.get('user_email'),
        'date_type': request.args.get('date_type'),
        'date_from': request.args.get('date_from'),
        'date_to': request.args.get('date_to'),
        'compliance_status': request.args.getlist('compliance_status[]')
    }
    if any(search_params.values()):
        current_span.set_attribute("params.count", sum(1 for v in search_params.values() if v))
        
        compliance_status_list = request.args.getlist('compliance_status[]')
        current_span.set_attribute("params.compliance_status_count", len(compliance_status_list))
        template_data = process_search_request(search_params, compliance_status_list, QueryManager=qm)
        return render_template(template_data['template'], **{k: v for k, v in template_data.items() if k != 'template'})
    template_data = process_index_request(QueryManager=qm)
    return render_template(template_data['template'], **{k: v for k, v in template_data.items() if k != 'template'})
    
@bp.route('/organization/<org_ids>')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.show_organization_dashboard")
def show_organization_dashboard(org_ids):
    current_span = trace.get_current_span()
    current_span.set_attribute("org_ids.length", len(org_ids))
    template_data = process_organization_dashboard_request(org_ids, QueryManager=qm)
    return render_template(template_data['template'], **{k: v for k, v in template_data.items() if k != 'template'})

@bp.route('/compare')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.show_compare_organizations_dashboard")
def show_compare_organizations_dashboard():
    current_span = trace.get_current_span()
    min_compliance = request.args.get('min_compliance')
    max_compliance = request.args.get('max_compliance')
    min_trials = request.args.get('min_trials')
    max_trials = request.args.get('max_trials')
    
    template_data = process_compare_organizations_request(min_compliance, max_compliance, min_trials, max_trials, QueryManager=qm)
    return render_template(template_data['template'], **{k: v for k, v in template_data.items() if k != 'template'})

@bp.route('/user/<int:user_id>')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.show_user_dashboard")
def show_user_dashboard(user_id):
    current_span = trace.get_current_span()
    current_span.set_attribute("user.id", int(user_id))
    def current_user_getter(uid):
        return current_user.get(uid)
    
    template_data = process_user_dashboard_request(user_id, current_user_getter, QueryManager=qm)
    return render_template(template_data['template'], **{k: v for k, v in template_data.items() if k != 'template'})

@bp.route('/reporting')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.reporting_dashboard")
def reporting_dashboard():
    current_span = trace.get_current_span()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    focus_org_id = request.args.get('org_focus', type=int)
    action_page = request.args.get('action_page', default=1, type=int)
    if start_date:
        current_span.set_attribute("filters.start_date", start_date)
    if end_date:
        current_span.set_attribute("filters.end_date", end_date)
    filter_args = {
        'min_compliance': request.args.get('min_compliance'),
        'max_compliance': request.args.get('max_compliance'),
        'funding_source_class': request.args.get('funding_source_class'),
        'organization': request.args.get('organization')
    }
    template_data = process_reporting_request(
        start_date,
        end_date,
        filters=filter_args,
        focus_org_id=focus_org_id,
        action_page=action_page,
        QueryManager=qm
    )
    return stream_template(template_data['template'], **{k: v for k, v in template_data.items() if k != 'template'})

@bp.route('/reporting/action-items/export')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.reporting_action_items_export")
def reporting_action_items_export():
    current_span = trace.get_current_span()
    filter_args = {
        'min_compliance': request.args.get('min_compliance'),
        'max_compliance': request.args.get('max_compliance'),
        'funding_source_class': request.args.get('funding_source_class'),
        'organization': request.args.get('organization')
    }
    rows = build_action_items_export_rows(filters=filter_args, QueryManager=qm)
    current_span.set_attribute("export.rows", len(rows))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Sponsor Name',
        'Trial Title',
        'NCT ID',
        'Status',
        'Start Date',
        'Completion Date',
        'Days Overdue'
    ])

    def _fmt(date_value):
        return date_value.strftime('%m/%d/%Y') if date_value else ''

    for row in rows:
        writer.writerow([
            row.get('organization_name', ''),
            row.get('title', ''),
            row.get('nct_id', ''),
            row.get('status', ''),
            _fmt(row.get('start_date')),
            _fmt(row.get('completion_date')),
            row.get('days_overdue', 0)
        ])

    csv_content = output.getvalue()
    output.close()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"action_items_{timestamp}.csv"
    response = make_response(csv_content)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@bp.route('/api/reporting/time-series')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.reporting_time_series")
def reporting_time_series():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    filter_args = {
        'min_compliance': request.args.get('min_compliance'),
        'max_compliance': request.args.get('max_compliance'),
        'funding_source_class': request.args.get('funding_source_class'),
        'organization': request.args.get('organization')
    }
    data = process_reporting_request(start_date, end_date, filters=filter_args, focus_org_id=None, QueryManager=qm)
    return jsonify({
        'time_series': data['time_series'],
        'status_keys': data['status_keys'],
        'start_date': data['start_date'],
        'end_date': data['end_date'],
        'kpis': data['kpis']
    })

# CSV Export Route
@bp.route('/export/csv')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.export_csv")
def export_csv():
    """Export current filtered data to CSV"""
    current_span = trace.get_current_span()
    # Get the same parameters as other routes
    search_params = {
        'title': request.args.get('title'),
        'nct_id': request.args.get('nct_id'),
        'organization': request.args.get('organization'),
        'user_email': request.args.get('user_email'),
        'date_type': request.args.get('date_type'),
        'date_from': request.args.get('date_from'),
        'date_to': request.args.get('date_to')
    }
    current_span.set_attribute("params.count", sum(1 for v in search_params.values() if v))
    
    compliance_status_list = request.args.getlist('compliance_status[]')
    export_type = request.args.get('type', 'trials')  # Default to trials export
    current_span.set_attribute("export.type", export_type)
    current_span.set_attribute("params.compliance_status_count", len(compliance_status_list))
    
    # Get data based on export type
    if export_type == 'organizations':
        min_compliance = request.args.get('min_compliance')
        max_compliance = request.args.get('max_compliance')
        min_trials = request.args.get('min_trials')
        max_trials = request.args.get('max_trials')
        funding_source_class = request.args.get('funding_source_class')
        organization_name = request.args.get('organization')
        
        org_compliance = qm.get_organization_risk_analysis(
            min_compliance=min_compliance,
            max_compliance=max_compliance,
            min_trials=min_trials,
            max_trials=max_trials,
            funding_source_class=funding_source_class,
            organization_name=organization_name
        )
        data = org_compliance
        filename = 'organizations_compliance_export'
        
        # Define CSV headers for organizations
        headers = [
            'Organization Name',
            'Total Trials',
            'Compliant Trials',
            'Non-Compliant Trials',
            'Pending Trials',
            'Compliance Rate (%)',
            'High Risk Trials',
            'Average Days Overdue'
        ]
        
        # Format data for CSV
        csv_data = []
        for org in data:
            compliance_rate = ((org.get('on_time_count', 0) / org.get('total_trials', 1) * 100) if org.get('total_trials', 0) > 0 else 0)
            avg_days_overdue = ((org.get('total_overdue_days', 0) / org.get('late_count', 1)) if org.get('late_count', 0) > 0 else 0)
            
            csv_data.append([
                org.get('name', ''),
                org.get('total_trials', 0),
                org.get('on_time_count', 0),
                org.get('late_count', 0),
                org.get('pending_count', 0),
                round(compliance_rate, 1),
                org.get('high_risk_trials', 0),
                round(avg_days_overdue, 1) if avg_days_overdue > 0 else 0
            ])
            
    elif export_type == 'user':
        user_id = request.args.get('user_id')
        if user_id:
            def current_user_getter(uid):
                return current_user.get(uid)
            template_data = process_user_dashboard_request(int(user_id), current_user_getter, QueryManager=qm)
            data = template_data.get('trials', [])
            filename = f'user_{user_id}_trials_export'
        else:
            template_data = process_search_request(search_params, compliance_status_list, QueryManager=qm)
            data = template_data.get('trials', [])
            filename = 'trials_export'
            
    else:
        # Default to trials export
        if any(search_params.values()) or compliance_status_list:
            template_data = process_search_request(search_params, compliance_status_list, QueryManager=qm)
        else:
            template_data = process_index_request(QueryManager=qm)
            
        data = template_data.get('trials', [])
        filename = 'trials_export'
    
    # For trials data (default case and user case)
    if export_type != 'organizations':
        # Define CSV headers for trials
        headers = [
            'Title',
            'NCT ID',
            'Organization',
            'User Email',
            'Status',
            'Start Date',
            'End Date',
            'Reporting Due Date'
        ]
        
        # Format data for CSV
        csv_data = []
        for trial in data:
            csv_data.append([
                trial.get('title', ''),
                trial.get('nct_id', ''),
                trial.get('name', ''),
                trial.get('email', ''),
                trial.get('status', ''),
                trial.get('start_date').strftime('%m/%d/%Y') if trial.get('start_date') else '',
                trial.get('completion_date').strftime('%m/%d/%Y') if trial.get('completion_date') else '',
                trial.get('reporting_due_date').strftime('%m/%d/%Y') if trial.get('reporting_due_date') else ''
            ])
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(headers)
    
    # Write data
    for row in csv_data:
        writer.writerow(row)
    
    # Create response
    csv_content = output.getvalue()
    output.close()
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename_with_timestamp = f"{filename}_{timestamp}.csv"
    current_span.set_attribute("export.rows", len(csv_data))
    
    # Create response with proper headers
    response = make_response(csv_content)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename_with_timestamp}"'
    
    return response

# Print Report Routes
@bp.route('/report/print')
@login_required    # pragma: no cover
@tracer.start_as_current_span("routes.print_report")
def print_report():
    """Generate a printable report based on current search/filter criteria"""
    current_span = trace.get_current_span()
    # Get search parameters from request (same as search route)
    search_params = {
        'title': request.args.get('title'),
        'nct_id': request.args.get('nct_id'),
        'organization': request.args.get('organization'),
        'user_email': request.args.get('user_email'),
        'date_type': request.args.get('date_type'),
        'date_from': request.args.get('date_from'),
        'date_to': request.args.get('date_to')
    }
    
    compliance_status_list = request.args.getlist('compliance_status[]')
    report_type = request.args.get('type', 'trials')  # Default to trials report
    current_span.set_attribute("report.type", report_type)
    
    # Process based on report type with enhanced analytics
    if report_type == 'organizations':
        min_compliance = request.args.get('min_compliance')
        max_compliance = request.args.get('max_compliance')
        min_trials = request.args.get('min_trials')
        max_trials = request.args.get('max_trials')
        funding_source_class = request.args.get('funding_source_class')
        organization_name = request.args.get('organization')
        
        # Use enhanced organization analysis
        org_compliance = qm.get_organization_risk_analysis(
            min_compliance=min_compliance,
            max_compliance=max_compliance,
            min_trials=min_trials,
            max_trials=max_trials,
            funding_source_class=funding_source_class,
            organization_name=organization_name
        )
        template_data = {
            'org_compliance': org_compliance,
            'on_time_count': sum(org.get('on_time_count', 0) for org in org_compliance),
            'late_count': sum(org.get('late_count', 0) for org in org_compliance),
        }
        
        # Get organization-level critical issues
        template_data['critical_issues'] = []
        for org in org_compliance:
            if org.get('high_risk_trials', 0) > 0:
                template_data['critical_issues'].append({
                    'type': 'High Risk Organization',
                    'priority': 'High',
                    'organization': org.get('name'),
                    'high_risk_trials': org.get('high_risk_trials'),
                    'description': f"{org.get('name')} has {org.get('high_risk_trials')} high-risk trials requiring attention"
                })
        
    elif report_type == 'user':
        user_id = request.args.get('user_id')
        if user_id:
            def current_user_getter(uid):
                return current_user.get(uid)
            template_data = process_user_dashboard_request(int(user_id), current_user_getter, QueryManager=qm)
        else:
            template_data = process_search_request(search_params, compliance_status_list, QueryManager=qm)
            
        # Get enhanced analytics for user data
        if template_data.get('trials'):
            enhanced_stats = qm.get_compliance_summary_stats(search_params, compliance_status_list)
            template_data.update(enhanced_stats)
            template_data['critical_issues'] = qm.get_critical_issues(search_params, compliance_status_list)
    else:
        # Default to trials report with enhanced analytics
        if any(search_params.values()) or compliance_status_list:
            template_data = process_search_request(search_params, compliance_status_list, QueryManager=qm)
        else:
            template_data = process_index_request(QueryManager=qm)
        
        # Get enhanced trial analytics
        enhanced_trials = qm.get_enhanced_trial_analytics(search_params, compliance_status_list)
        enhanced_stats = qm.get_compliance_summary_stats(search_params, compliance_status_list)
        critical_issues = qm.get_critical_issues(search_params, compliance_status_list)
        
        # Update template data with enhanced information
        template_data.update(enhanced_stats)
        template_data['enhanced_trials'] = enhanced_trials
        template_data['critical_issues'] = critical_issues
    
    # Add report metadata
    from datetime import datetime
    template_data['report_generated'] = datetime.now()
    template_data['report_type'] = report_type
    template_data['search_params'] = search_params
    template_data['compliance_status_list'] = compliance_status_list
    
    return render_template('reports/print_report.html', **{k: v for k, v in template_data.items() if k != 'template'})


@bp.route('/query-workspace')
@login_required    # pragma: no cover
def query_workspace():
    try:
        tool_definitions = mcp_server.get_tools()
    except Exception as exc:    # pragma: no cover
        current_app.logger.warning("Failed to load MCP tool definitions: %s", exc)
        tool_definitions = []

    tool_schema = json.dumps(tool_definitions[0], indent=2) if tool_definitions else "{}"

    context = {
        'features': README_FEATURES,
        'parameter_sections': PARAMETER_SECTIONS,
        'quick_start_snippets': QUICK_START_SNIPPETS,
        'integration_snippets': INTEGRATION_SNIPPETS,
        'sample_prompts': SAMPLE_PROMPTS,
        'tool_schema': tool_schema,
        'default_use_llm': DEFAULT_USE_LLM,
        'anthropic_configured': bool(ANTHROPIC_API_KEY),
        'welcome_message': WELCOME_MESSAGE,
        'readme_source': README_SOURCE,
        'integration_source': INTEGRATION_SOURCE,
    }
    return render_template('query_workspace.html', **context)


@bp.route('/api/query-workspace/message', methods=['POST'])
@login_required    # pragma: no cover
def handle_query_workspace_message():
    payload = request.get_json(silent=True) or {}
    message = (payload.get('message') or '').strip()
    prefer_llm = _coerce_bool(payload.get('use_llm'))

    if not message:
        return jsonify({'success': False, 'error': 'A query is required.'}), 400

    try:
        session_entry = _ensure_workspace_session(current_user.id, prefer_llm=prefer_llm)
        response = session_entry['interface'].process_query(message)
        sanitized_message = _sanitize_message(response.get('message', ''))
        return jsonify({
            'success': True,
            'status': response.get('status'),
            'message': sanitized_message,
            'clarifications': response.get('clarifications', []),
            'params': response.get('params', {}),
            'result': response.get('result'),
            'use_llm': session_entry['interface'].use_llm,
        })
    except Exception as exc:    # pragma: no cover
        current_app.logger.exception("Query workspace message failed: %s", exc)
        return jsonify({'success': False, 'error': 'Unable to process the query.'}), 500


@bp.route('/api/query-workspace/reset', methods=['POST'])
@login_required    # pragma: no cover
def reset_query_workspace():
    payload = request.get_json(silent=True) or {}
    prefer_llm = _coerce_bool(payload.get('use_llm'))
    session_entry = _reset_workspace_session(current_user.id, prefer_llm=prefer_llm)
    return jsonify({
        'success': True,
        'message': 'Conversation reset.',
        'use_llm': session_entry['interface'].use_llm,
    })
