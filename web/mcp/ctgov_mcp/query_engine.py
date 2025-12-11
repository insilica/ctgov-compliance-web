#!/usr/bin/env python3
"""
MCP-style ClinicalTrials.gov Query Interface

Provides flexible querying of ClinicalTrials.gov with natural language support.
"""

import requests
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import re


class ClinicalTrialsQueryBuilder:
    """Builds API query parameters from structured inputs"""

    def __init__(self):
        self.base_url = "https://clinicaltrials.gov/api/v2/studies"
        self.reset()

    def reset(self):
        """Reset all query parameters"""
        self.params = {
            "format": "json",
            "countTotal": "true",
            "pageSize": 1
        }
        self.filter_conditions = []
        self.post_filter_conditions = []
        self.agg_filters = []

    def set_study_type(self, study_type: str):
        """
        Set study type filter
        Options: Interventional, Observational, Expanded Access
        """
        if study_type:
            self.filter_conditions.append(f"AREA[StudyType]{study_type}")
        return self

    def set_results_filter(self, has_results: Optional[bool] = None):
        """
        Filter by results availability
        None = no filter, True = with results, False = without results
        """
        if has_results is True:
            self.agg_filters.append("results:with")
        elif has_results is False:
            self.agg_filters.append("results:without")
        return self

    def set_publications_filter(self, has_publications: Optional[bool] = None):
        """
        Filter by publications/references
        None = no filter, True = has publications, False = no publications
        """
        if has_publications is True:
            self.filter_conditions.append("NOT AREA[Reference]MISSING")
        elif has_publications is False:
            self.filter_conditions.append("AREA[Reference]MISSING")
        return self

    def set_status(self, status: Union[str, List[str]]):
        """
        Set study status filter
        Options: com (completed), rec (recruiting), not (not yet recruiting),
                 act (active, not recruiting), sus (suspended), ter (terminated),
                 wit (withdrawn), unk (unknown)
        """
        if status:
            if isinstance(status, str):
                status = [status]
            for s in status:
                self.agg_filters.append(f"status:{s}")
        return self

    def set_phase(self, phases: Union[str, List[str]], exclude: bool = False):
        """
        Set phase filter
        Options: EARLY_PHASE1, PHASE1, PHASE2, PHASE3, PHASE4, NA
        """
        if phases:
            if isinstance(phases, str):
                phases = [phases]

            phase_expr = " OR ".join(phases)
            if exclude:
                self.filter_conditions.append(f"NOT AREA[Phase]({phase_expr})")
            else:
                self.filter_conditions.append(f"AREA[Phase]({phase_expr})")
        return self

    def set_fda_regulated(self, drug: Optional[bool] = None, device: Optional[bool] = None):
        """Set FDA regulation filters"""
        if drug is True:
            self.filter_conditions.append("AREA[IsFDARegulatedDrug]true")
        if device is True:
            self.filter_conditions.append("AREA[IsFDARegulatedDevice]true")
        return self

    def set_location(self, country: Optional[str] = None, state: Optional[str] = None, city: Optional[str] = None):
        """Set location filters"""
        if country:
            self.params["query.locn"] = f"AREA[LocationCountry]{country}"
        if state:
            self.params["query.locn"] = f"AREA[LocationState]{state}"
        if city:
            self.params["query.locn"] = f"AREA[LocationCity]{city}"
        return self

    def set_date_range(self,
                       start_date_min: Optional[str] = None,
                       start_date_max: Optional[str] = None,
                       completion_date_min: Optional[str] = None,
                       completion_date_max: Optional[str] = None):
        """
        Set date range filters
        Dates should be in YYYY-MM-DD format
        """
        if start_date_min or start_date_max:
            min_val = start_date_min or "MIN"
            max_val = start_date_max or "MAX"
            self.post_filter_conditions.append(f"AREA[StartDate]RANGE[{min_val},{max_val}]")

        if completion_date_min or completion_date_max:
            min_val = completion_date_min or "MIN"
            max_val = completion_date_max or "MAX"
            self.post_filter_conditions.append(f"AREA[CompletionDate]RANGE[{min_val},{max_val}]")

        return self

    def set_condition(self, condition: str):
        """Search by condition/disease"""
        if condition:
            self.params["query.cond"] = condition
        return self

    def set_intervention(self, intervention: str):
        """Search by intervention/treatment"""
        if intervention:
            self.params["query.intr"] = intervention
        return self

    def set_sponsor(self, sponsor: str):
        """Search by sponsor/collaborator"""
        if sponsor:
            self.params["query.spons"] = sponsor
        return self

    def set_keywords(self, keywords: str):
        """Search by keywords"""
        if keywords:
            self.params["query.term"] = keywords
        return self

    def set_page_size(self, size: int):
        """Set number of results to return (default 1 for counting)"""
        self.params["pageSize"] = size
        return self

    def set_fields(self, fields: List[str]):
        """Set which fields to return"""
        if fields:
            self.params["fields"] = ",".join(fields)
        return self

    def build(self) -> Dict[str, Any]:
        """Build final query parameters"""
        # Combine filter conditions
        if self.filter_conditions:
            self.params["filter.advanced"] = " AND ".join(self.filter_conditions)

        # Combine post-filter conditions
        if self.post_filter_conditions:
            self.params["postFilter.advanced"] = " AND ".join(self.post_filter_conditions)

        # Combine aggregation filters
        if self.agg_filters:
            self.params["aggFilters"] = ",".join(self.agg_filters)

        return self.params


class ClinicalTrialsQuery:
    """Main query executor for ClinicalTrials.gov"""

    def __init__(self):
        self.base_url = "https://clinicaltrials.gov/api/v2/studies"

    def execute_query(self, params: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        """Execute a query and return results"""
        try:
            response = requests.get(self.base_url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            return {
                "success": True,
                "total_count": data.get("totalCount", 0),
                "studies": data.get("studies", []),
                "params_used": params
            }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": "request_error"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": "unknown_error"
            }

    def count_trials(self, **kwargs) -> Dict[str, Any]:
        """
        Count trials with flexible parameters

        Args:
            study_type: str - Interventional, Observational, etc.
            has_results: bool - Filter by results availability
            has_publications: bool - Filter by publications
            status: str or list - Study status (com, rec, etc.)
            phase: str or list - Study phase
            exclude_phase: bool - Whether to exclude specified phases
            fda_drug: bool - FDA regulated drug
            fda_device: bool - FDA regulated device
            country: str - Location country
            state: str - Location state
            city: str - Location city
            start_date_min: str - Start date minimum (YYYY-MM-DD)
            start_date_max: str - Start date maximum (YYYY-MM-DD)
            completion_date_min: str - Completion date minimum (YYYY-MM-DD)
            completion_date_max: str - Completion date maximum (YYYY-MM-DD)
            condition: str - Disease/condition
            intervention: str - Treatment/intervention
            sponsor: str - Sponsor name
            keywords: str - Search keywords

        Returns:
            Dict with query results
        """
        builder = ClinicalTrialsQueryBuilder()

        # Apply filters
        if 'study_type' in kwargs:
            builder.set_study_type(kwargs['study_type'])

        if 'has_results' in kwargs:
            builder.set_results_filter(kwargs['has_results'])

        if 'has_publications' in kwargs:
            builder.set_publications_filter(kwargs['has_publications'])

        if 'status' in kwargs:
            builder.set_status(kwargs['status'])

        if 'phase' in kwargs:
            exclude = kwargs.get('exclude_phase', False)
            builder.set_phase(kwargs['phase'], exclude=exclude)

        if 'fda_drug' in kwargs or 'fda_device' in kwargs:
            builder.set_fda_regulated(
                drug=kwargs.get('fda_drug'),
                device=kwargs.get('fda_device')
            )

        if 'country' in kwargs or 'state' in kwargs or 'city' in kwargs:
            builder.set_location(
                country=kwargs.get('country'),
                state=kwargs.get('state'),
                city=kwargs.get('city')
            )

        # Date ranges
        if any(k in kwargs for k in ['start_date_min', 'start_date_max', 'completion_date_min', 'completion_date_max']):
            builder.set_date_range(
                start_date_min=kwargs.get('start_date_min'),
                start_date_max=kwargs.get('start_date_max'),
                completion_date_min=kwargs.get('completion_date_min'),
                completion_date_max=kwargs.get('completion_date_max')
            )

        # Search terms
        if 'condition' in kwargs:
            builder.set_condition(kwargs['condition'])

        if 'intervention' in kwargs:
            builder.set_intervention(kwargs['intervention'])

        if 'sponsor' in kwargs:
            builder.set_sponsor(kwargs['sponsor'])

        if 'keywords' in kwargs:
            builder.set_keywords(kwargs['keywords'])

        # Build and execute
        params = builder.build()
        return self.execute_query(params)


# MCP-style tool functions
def mcp_count_trials(**kwargs) -> str:
    """
    MCP Tool: Count clinical trials with flexible filtering

    This tool queries ClinicalTrials.gov and returns counts based on various filters.

    Parameters:
        study_type: Type of study (Interventional, Observational, Expanded Access)
        has_results: True/False to filter by results availability
        has_publications: True/False to filter by publications in references
        status: Study status (completed, recruiting, etc.)
        phase: Study phase (PHASE1, PHASE2, PHASE3, PHASE4, EARLY_PHASE1, NA)
        exclude_phase: Exclude specified phases instead of including
        fda_drug: FDA regulated drug (True/False)
        fda_device: FDA regulated device (True/False)
        country: Location country (e.g., "United States")
        state: Location state
        city: Location city
        start_date_min: Minimum start date (YYYY-MM-DD)
        start_date_max: Maximum start date (YYYY-MM-DD)
        completion_date_min: Minimum completion date (YYYY-MM-DD)
        completion_date_max: Maximum completion date (YYYY-MM-DD)
        condition: Disease or condition (e.g., "diabetes")
        intervention: Treatment or intervention (e.g., "aspirin")
        sponsor: Sponsor name
        keywords: General search keywords

    Returns:
        Formatted string with count and query details
    """
    query = ClinicalTrialsQuery()
    result = query.count_trials(**kwargs)

    if result["success"]:
        output = f"✓ Query executed successfully\n\n"
        output += f"Total trials found: {result['total_count']:,}\n\n"

        # Show applied filters
        output += "Filters applied:\n"
        for key, value in kwargs.items():
            output += f"  • {key}: {value}\n"

        return output
    else:
        return f"✗ Query failed: {result['error']}"


def mcp_get_trial_details(**kwargs) -> str:
    """
    MCP Tool: Get detailed information about trials

    Same parameters as mcp_count_trials, but returns up to 10 trial details.
    """
    # Modify kwargs to request more data
    query_kwargs = kwargs.copy()

    query = ClinicalTrialsQuery()
    builder = ClinicalTrialsQueryBuilder()

    # Apply all filters like count_trials
    if 'study_type' in kwargs:
        builder.set_study_type(kwargs['study_type'])
    if 'has_results' in kwargs:
        builder.set_results_filter(kwargs['has_results'])
    if 'has_publications' in kwargs:
        builder.set_publications_filter(kwargs['has_publications'])
    if 'status' in kwargs:
        builder.set_status(kwargs['status'])
    if 'phase' in kwargs:
        builder.set_phase(kwargs['phase'], exclude=kwargs.get('exclude_phase', False))
    if 'fda_drug' in kwargs or 'fda_device' in kwargs:
        builder.set_fda_regulated(
            drug=kwargs.get('fda_drug'),
            device=kwargs.get('fda_device')
        )
    if 'country' in kwargs or 'state' in kwargs or 'city' in kwargs:
        builder.set_location(
            country=kwargs.get('country'),
            state=kwargs.get('state'),
            city=kwargs.get('city')
        )
    if any(k in kwargs for k in ['start_date_min', 'start_date_max', 'completion_date_min', 'completion_date_max']):
        builder.set_date_range(
            start_date_min=kwargs.get('start_date_min'),
            start_date_max=kwargs.get('start_date_max'),
            completion_date_min=kwargs.get('completion_date_min'),
            completion_date_max=kwargs.get('completion_date_max')
        )
    if 'condition' in kwargs:
        builder.set_condition(kwargs['condition'])
    if 'intervention' in kwargs:
        builder.set_intervention(kwargs['intervention'])
    if 'sponsor' in kwargs:
        builder.set_sponsor(kwargs['sponsor'])
    if 'keywords' in kwargs:
        builder.set_keywords(kwargs['keywords'])

    # Request more details
    builder.set_page_size(10)
    builder.set_fields([
        "NCTId", "BriefTitle", "OverallStatus", "HasResults",
        "StartDate", "CompletionDate", "Phase", "StudyType"
    ])

    params = builder.build()
    result = query.execute_query(params)

    if result["success"]:
        output = f"✓ Found {result['total_count']:,} trials (showing first 10)\n\n"

        for i, study in enumerate(result["studies"][:10], 1):
            protocol = study.get("protocolSection", {})
            ident = protocol.get("identificationModule", {})
            status_mod = protocol.get("statusModule", {})
            design = protocol.get("designModule", {})

            nct_id = ident.get("nctId", "Unknown")
            title = ident.get("briefTitle", "No title")
            overall_status = status_mod.get("overallStatus", "Unknown")

            output += f"{i}. {nct_id}\n"
            output += f"   Title: {title[:70]}...\n"
            output += f"   Status: {overall_status}\n"
            output += f"\n"

        return output
    else:
        return f"✗ Query failed: {result['error']}"


if __name__ == "__main__":
    # Example usage
    query = ClinicalTrialsQuery()

    # Example 1: Count all interventional trials with results
    print("Example 1: Interventional trials with results")
    print("=" * 70)
    result = query.count_trials(
        study_type="Interventional",
        has_results=True
    )
    if result["success"]:
        print(f"Count: {result['total_count']:,}")
    print()

    # Example 2: ACT trials (completed, no results, no publications)
    print("Example 2: ACT trials (completed, no results, no publications)")
    print("=" * 70)
    today = datetime.now()
    one_year_ago = today - timedelta(days=365)

    result = query.count_trials(
        study_type="Interventional",
        status="com",
        has_results=False,
        has_publications=False,
        country="United States",
        completion_date_max=one_year_ago.strftime("%Y-%m-%d"),
        phase=["PHASE2", "PHASE3", "PHASE4"],
        fda_drug=True
    )
    if result["success"]:
        print(f"Count: {result['total_count']:,}")
    print()
