#!/usr/bin/env python3
"""
Natural Language Parser for ClinicalTrials.gov Queries

Converts natural language queries into structured API parameters.
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta


class NaturalLanguageParser:
    """Parses natural language queries into ClinicalTrials.gov API parameters"""

    def __init__(self):
        self.study_type_keywords = {
            'interventional': 'Interventional',
            'observational': 'Observational',
            'expanded access': 'Expanded Access',
            'intervention': 'Interventional',
            'observe': 'Observational',
            'clinical trial': 'Interventional'
        }

        self.status_keywords = {
            'completed': 'com',
            'recruiting': 'rec',
            'not yet recruiting': 'not',
            'active': 'act',
            'suspended': 'sus',
            'terminated': 'ter',
            'withdrawn': 'wit',
            'unknown': 'unk'
        }

        self.phase_keywords = {
            'phase 1': 'PHASE1',
            'phase 2': 'PHASE2',
            'phase 3': 'PHASE3',
            'phase 4': 'PHASE4',
            'phase i': 'PHASE1',
            'phase ii': 'PHASE2',
            'phase iii': 'PHASE3',
            'phase iv': 'PHASE4',
            'early phase 1': 'EARLY_PHASE1',
            'early phase': 'EARLY_PHASE1',
            'phase1': 'PHASE1',
            'phase2': 'PHASE2',
            'phase3': 'PHASE3',
            'phase4': 'PHASE4'
        }

        self.country_keywords = {
            'usa': 'United States',
            'us': 'United States',
            'united states': 'United States',
            'america': 'United States',
            'uk': 'United Kingdom',
            'united kingdom': 'United Kingdom'
        }

    def parse(self, query: str) -> Tuple[Dict[str, Any], List[str]]:
        """
        Parse natural language query into API parameters

        Returns:
            Tuple of (parameters dict, list of clarification questions)
        """
        query_lower = query.lower()
        params = {}
        clarifications = []

        # Extract study type
        study_type = self._extract_study_type(query_lower)
        if study_type:
            params['study_type'] = study_type

        # Extract results filter
        results_filter = self._extract_results_filter(query_lower)
        if results_filter is not None:
            params['has_results'] = results_filter

        # Extract publications filter
        pubs_filter = self._extract_publications_filter(query_lower)
        if pubs_filter is not None:
            params['has_publications'] = pubs_filter

        # Extract status
        status = self._extract_status(query_lower)
        if status:
            params['status'] = status

        # Extract phase
        phase, exclude = self._extract_phase(query_lower)
        if phase:
            params['phase'] = phase
            if exclude:
                params['exclude_phase'] = True

        # Extract FDA regulation
        fda_drug, fda_device = self._extract_fda_regulation(query_lower)
        if fda_drug:
            params['fda_drug'] = True
        if fda_device:
            params['fda_device'] = True

        # Extract location
        country = self._extract_country(query_lower)
        if country:
            params['country'] = country

        # Extract dates
        date_params = self._extract_dates(query_lower)
        params.update(date_params)

        # Extract condition/disease
        condition = self._extract_condition(query_lower)
        if condition:
            params['condition'] = condition

        # Extract intervention
        intervention = self._extract_intervention(query_lower)
        if intervention:
            params['intervention'] = intervention

        # Extract sponsor
        sponsor = self._extract_sponsor(query_lower)
        if sponsor:
            params['sponsor'] = sponsor

        # Check for ACT (Applicable Clinical Trial) pattern
        if self._is_act_query(query_lower):
            act_params = self._get_act_parameters()
            params.update(act_params)

        # Generate clarification questions if needed
        clarifications = self._generate_clarifications(query_lower, params)

        return params, clarifications

    def _extract_study_type(self, query: str) -> Optional[str]:
        """Extract study type from query"""
        for keyword, study_type in self.study_type_keywords.items():
            if keyword in query:
                return study_type
        return None

    def _extract_results_filter(self, query: str) -> Optional[bool]:
        """Extract results filter from query"""
        if 'with results' in query or 'has results' in query or 'results posted' in query:
            return True
        elif 'without results' in query or 'no results' in query or 'missing results' in query:
            return False
        return None

    def _extract_publications_filter(self, query: str) -> Optional[bool]:
        """Extract publications filter from query"""
        if 'with publication' in query or 'has publication' in query:
            return True
        elif 'without publication' in query or 'no publication' in query or 'missing publication' in query:
            return False
        return None

    def _extract_status(self, query: str) -> Optional[str]:
        """Extract study status from query"""
        for keyword, status_code in self.status_keywords.items():
            if keyword in query:
                return status_code
        return None

    def _extract_phase(self, query: str) -> Tuple[Optional[List[str]], bool]:
        """Extract phase from query, returns (phases, exclude_flag)"""
        phases = []
        exclude = False

        # Check for exclusion patterns
        if 'not phase' in query or 'exclude phase' in query or 'except phase' in query:
            exclude = True

        for keyword, phase_code in self.phase_keywords.items():
            if keyword in query:
                phases.append(phase_code)

        # Check for phase range (e.g., "phase 2/3")
        phase_range_match = re.search(r'phase (\d)[/\-](\d)', query)
        if phase_range_match:
            start, end = phase_range_match.groups()
            for i in range(int(start), int(end) + 1):
                phases.append(f'PHASE{i}')

        return phases if phases else None, exclude

    def _extract_fda_regulation(self, query: str) -> Tuple[bool, bool]:
        """Extract FDA regulation info"""
        fda_drug = 'fda drug' in query or 'fda regulated drug' in query or 'fda-regulated drug' in query
        fda_device = 'fda device' in query or 'fda regulated device' in query or 'fda-regulated device' in query
        return fda_drug, fda_device

    def _extract_country(self, query: str) -> Optional[str]:
        """Extract country from query"""
        for keyword, country in self.country_keywords.items():
            if keyword in query:
                return country

        # Try to extract "in [Country]"
        country_match = re.search(r'in ([A-Z][a-z]+(?: [A-Z][a-z]+)*)', query)
        if country_match:
            return country_match.group(1)

        return None

    def _extract_dates(self, query: str) -> Dict[str, str]:
        """Extract date ranges from query"""
        params = {}
        today = datetime.now()

        # Check for relative dates
        if 'completed more than' in query or 'completed over' in query:
            match = re.search(r'completed (?:more than|over) (\d+) year', query)
            if match:
                years = int(match.group(1))
                date = today - timedelta(days=365 * years)
                params['completion_date_max'] = date.strftime('%Y-%m-%d')

        if 'completed within' in query or 'completed in the last' in query:
            match = re.search(r'(?:within|in the last) (\d+) year', query)
            if match:
                years = int(match.group(1))
                date = today - timedelta(days=365 * years)
                params['completion_date_min'] = date.strftime('%Y-%m-%d')

        if 'started after' in query:
            match = re.search(r'started after (\d{4})', query)
            if match:
                params['start_date_min'] = f"{match.group(1)}-01-01"

        if 'started before' in query:
            match = re.search(r'started before (\d{4})', query)
            if match:
                params['start_date_max'] = f"{match.group(1)}-12-31"

        # Extract specific dates (YYYY-MM-DD or YYYY)
        date_pattern = r'(\d{4}(?:-\d{2}-\d{2})?)'
        dates = re.findall(date_pattern, query)

        if 'from' in query and 'to' in query and len(dates) >= 2:
            params['start_date_min'] = dates[0] if len(dates[0]) == 4 else dates[0]
            params['start_date_max'] = dates[1] if len(dates[1]) == 4 else dates[1]

        return params

    def _extract_condition(self, query: str) -> Optional[str]:
        """Extract condition/disease from query"""
        # Look for "for [condition]" or "with [condition]"
        match = re.search(r'(?:for|with|treating|treat) ((?:cancer|diabetes|covid|hypertension|alzheimer|parkinson|depression|anxiety)[a-z]*)', query)
        if match:
            return match.group(1)

        return None

    def _extract_intervention(self, query: str) -> Optional[str]:
        """Extract intervention/treatment from query"""
        # Look for "using [intervention]" or "drug [name]"
        match = re.search(r'(?:using|drug|treatment|therapy) ([a-z]+)', query)
        if match:
            return match.group(1)

        return None

    def _extract_sponsor(self, query: str) -> Optional[str]:
        """Extract sponsor from query"""
        # Look for "sponsored by [sponsor]" or "by [sponsor]"
        match = re.search(r'(?:sponsored by|by sponsor) ([A-Z][a-zA-Z ]+)', query)
        if match:
            return match.group(1).strip()

        return None

    def _is_act_query(self, query: str) -> bool:
        """Check if query is asking for ACT (Applicable Clinical Trial) data"""
        act_keywords = ['act', 'applicable clinical trial', 'non-compliant', 'noncompliant']
        return any(keyword in query for keyword in act_keywords)

    def _get_act_parameters(self) -> Dict[str, Any]:
        """Get standard ACT parameters"""
        today = datetime.now()
        one_year_ago = today - timedelta(days=365)

        return {
            'study_type': 'Interventional',
            'status': 'com',
            'has_results': False,
            'has_publications': False,
            'country': 'United States',
            'completion_date_max': one_year_ago.strftime('%Y-%m-%d'),
            'start_date_min': '2017-01-01',
            'phase': ['PHASE2', 'PHASE3', 'PHASE4'],
            'fda_drug': True
        }

    def _generate_clarifications(self, query: str, params: Dict[str, Any]) -> List[str]:
        """Generate clarification questions based on ambiguous or missing info"""
        clarifications = []

        # If no study type specified
        if 'study_type' not in params and not self._is_act_query(query):
            if 'trial' in query or 'stud' in query:
                clarifications.append(
                    "What type of studies are you interested in? (Interventional, Observational, or all types)"
                )

        # If asking about results but not clear if with or without
        if 'result' in query and 'has_results' not in params:
            if not ('with' in query or 'without' in query):
                clarifications.append(
                    "Are you looking for studies WITH results posted or WITHOUT results posted?"
                )

        # If asking about publications but not clear
        if 'publication' in query and 'has_publications' not in params:
            if not ('with' in query or 'without' in query):
                clarifications.append(
                    "Are you looking for studies WITH publications or WITHOUT publications?"
                )

        # If date mentioned but not fully specified
        if ('date' in query or 'completed' in query or 'started' in query) and \
           not any(k in params for k in ['start_date_min', 'start_date_max', 'completion_date_min', 'completion_date_max']):
            clarifications.append(
                "Could you specify the date range you're interested in? (e.g., 'completed in the last year' or 'started after 2017')"
            )

        return clarifications


def format_query_summary(params: Dict[str, Any]) -> str:
    """Format parameters into a human-readable summary"""
    lines = ["Query Parameters:"]

    if 'study_type' in params:
        lines.append(f"  • Study Type: {params['study_type']}")

    if 'has_results' in params:
        lines.append(f"  • Results: {'WITH results' if params['has_results'] else 'WITHOUT results'}")

    if 'has_publications' in params:
        lines.append(f"  • Publications: {'WITH publications' if params['has_publications'] else 'WITHOUT publications'}")

    if 'status' in params:
        status_map = {'com': 'Completed', 'rec': 'Recruiting', 'act': 'Active'}
        status_name = status_map.get(params['status'], params['status'])
        lines.append(f"  • Status: {status_name}")

    if 'phase' in params:
        phases = params['phase'] if isinstance(params['phase'], list) else [params['phase']]
        exclude = params.get('exclude_phase', False)
        phase_str = ', '.join(phases)
        lines.append(f"  • Phase: {'EXCLUDING' if exclude else 'INCLUDING'} {phase_str}")

    if 'country' in params:
        lines.append(f"  • Country: {params['country']}")

    if 'fda_drug' in params and params['fda_drug']:
        lines.append(f"  • FDA Regulated: Drug")

    if 'fda_device' in params and params['fda_device']:
        lines.append(f"  • FDA Regulated: Device")

    if 'completion_date_max' in params:
        lines.append(f"  • Completed before: {params['completion_date_max']}")

    if 'completion_date_min' in params:
        lines.append(f"  • Completed after: {params['completion_date_min']}")

    if 'start_date_min' in params:
        lines.append(f"  • Started after: {params['start_date_min']}")

    if 'start_date_max' in params:
        lines.append(f"  • Started before: {params['start_date_max']}")

    if 'condition' in params:
        lines.append(f"  • Condition: {params['condition']}")

    if 'intervention' in params:
        lines.append(f"  • Intervention: {params['intervention']}")

    if 'sponsor' in params:
        lines.append(f"  • Sponsor: {params['sponsor']}")

    return '\n'.join(lines)


if __name__ == "__main__":
    # Test the parser
    parser = NaturalLanguageParser()

    test_queries = [
        "How many interventional trials have results posted?",
        "Count completed trials without results in the United States",
        "Show me ACT trials",
        "Interventional trials for diabetes with publications",
        "Phase 2/3 trials completed in the last year",
        "Trials with FDA regulated drugs but no results"
    ]

    print("=" * 70)
    print("NATURAL LANGUAGE PARSER TESTS")
    print("=" * 70)

    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 70)
        params, clarifications = parser.parse(query)
        print(format_query_summary(params))

        if clarifications:
            print("\nClarifications needed:")
            for q in clarifications:
                print(f"  ? {q}")
        print()
