#!/usr/bin/env python3
"""
LLM-based Natural Language Parser for ClinicalTrials.gov Queries

Uses Claude (Anthropic API) to parse natural language queries into
structured API parameters with intelligent clarification questions.
"""

import os
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import anthropic


class LLMQueryParser:
    """Uses Claude to parse natural language queries into structured parameters"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the LLM parser

        Args:
            api_key: Anthropic API key (or set ANTHROPIC_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. "
                "Set ANTHROPIC_API_KEY environment variable or pass api_key parameter."
            )

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.conversation_history = []

    def parse(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], List[str], str]:
        """
        Parse natural language query using Claude

        Args:
            query: User's natural language query
            context: Optional context from previous conversation

        Returns:
            Tuple of (parameters dict, clarification questions list, explanation)
        """
        # Build the system prompt with parameter documentation
        system_prompt = self._build_system_prompt()

        # Build the user message
        user_message = self._build_user_message(query, context)

        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        try:
            # Call Claude
            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2000,
                system=system_prompt,
                messages=self.conversation_history
            )

            # Extract the response
            response_text = response.content[0].text

            # Add assistant response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": response_text
            })

            # Parse the JSON response
            result = self._parse_response(response_text)

            return (
                result.get("parameters", {}),
                result.get("clarifications", []),
                result.get("explanation", "")
            )

        except Exception as e:
            return {}, [], f"Error parsing query: {str(e)}"

    def _build_system_prompt(self) -> str:
        """Build the system prompt with parameter documentation"""
        today = datetime.now().strftime("%Y-%m-%d")

        return f"""You are a specialized parser for ClinicalTrials.gov queries. Your job is to convert natural language queries into structured API parameters.

**Today's date:** {today}

# Available Parameters

## Study Filters
- `study_type`: "Interventional", "Observational", "Expanded Access"
- `status`: Study status codes
  - "com" = Completed
  - "rec" = Recruiting
  - "not" = Not yet recruiting
  - "act" = Active, not recruiting
  - "sus" = Suspended
  - "ter" = Terminated
  - "wit" = Withdrawn
- `phase`: List of phases (can include multiple)
  - "PHASE1", "PHASE2", "PHASE3", "PHASE4", "EARLY_PHASE1", "NA"
- `exclude_phase`: Boolean - if true, exclude specified phases instead of including

## Results & Publications
- `has_results`: true/false - whether results are posted on ClinicalTrials.gov
- `has_publications`: true/false - whether publications are listed in references

## Regulatory
- `fda_drug`: true - FDA regulated drug
- `fda_device`: true - FDA regulated device

## Location
- `country`: Country name (e.g., "United States")
- `state`: State name
- `city`: City name

## Dates (YYYY-MM-DD format)
- `start_date_min`: Minimum start date
- `start_date_max`: Maximum start date
- `completion_date_min`: Minimum completion date
- `completion_date_max`: Maximum completion date

## Search Terms
- `condition`: Disease/condition (e.g., "diabetes", "cancer")
- `intervention`: Treatment/intervention (e.g., "aspirin", "chemotherapy")
- `sponsor`: Sponsor organization name
- `keywords`: General search keywords

# Special Query Types

## ACT (Applicable Clinical Trial) Queries
When user asks for "ACT trials", "applicable clinical trials", or "non-compliant trials", apply these criteria:
- study_type: "Interventional"
- status: "com" (completed)
- has_results: false
- has_publications: false
- country: "United States"
- completion_date_max: one year ago from today
- start_date_min: "2017-01-01"
- phase: ["PHASE2", "PHASE3", "PHASE4"]
- fda_drug: true

# Response Format

You must ALWAYS respond with valid JSON in this exact format:

```json
{{
  "parameters": {{
    // Extracted parameters as key-value pairs
    // Only include parameters you're confident about
  }},
  "clarifications": [
    // List of questions to ask user if anything is ambiguous
    // Empty array if no clarifications needed
  ],
  "explanation": "Brief explanation of what you understood from the query"
}}
```

# Instructions

1. Parse the user's query and extract all possible parameters
2. Be conservative - only include parameters you're confident about
3. If anything is ambiguous, add clarification questions
4. Handle relative dates (e.g., "last year", "in 2020", "over 1 year ago")
5. Recognize synonyms (e.g., "US" = "United States", "with results" = has_results: true)
6. For complex queries, break down into components
7. ALWAYS respond with valid JSON - no additional text outside the JSON

# Examples

User: "How many interventional trials have results?"
Response:
```json
{{
  "parameters": {{
    "study_type": "Interventional",
    "has_results": true
  }},
  "clarifications": [],
  "explanation": "Looking for interventional studies that have results posted"
}}
```

User: "Completed trials without results in the US"
Response:
```json
{{
  "parameters": {{
    "status": "com",
    "has_results": false,
    "country": "United States"
  }},
  "clarifications": [
    "What type of studies? (Interventional, Observational, or all types)"
  ],
  "explanation": "Looking for completed trials without results in the United States, but need to know study type"
}}
```

User: "Show me ACT trials"
Response:
```json
{{
  "parameters": {{
    "study_type": "Interventional",
    "status": "com",
    "has_results": false,
    "has_publications": false,
    "country": "United States",
    "completion_date_max": "{(datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')}",
    "start_date_min": "2017-01-01",
    "phase": ["PHASE2", "PHASE3", "PHASE4"],
    "fda_drug": true
  }},
  "clarifications": [],
  "explanation": "Applying ACT (Applicable Clinical Trial) criteria for non-compliant trials"
}}
```

Remember: ONLY output JSON, no other text!"""

    def _build_user_message(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build the user message with optional context"""
        message = f"Query: {query}"

        if context:
            message += f"\n\nPrevious parameters: {json.dumps(context, indent=2)}"
            message += "\n\n(User is refining or adding to previous query. Merge with existing parameters.)"

        return message

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the JSON response from Claude"""
        try:
            # Extract JSON from code blocks if present
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()

            # Parse JSON
            result = json.loads(response_text)
            return result

        except json.JSONDecodeError as e:
            return {
                "parameters": {},
                "clarifications": [f"I had trouble understanding that. Could you rephrase?"],
                "explanation": f"JSON parse error: {str(e)}"
            }

    def reset(self):
        """Reset conversation history"""
        self.conversation_history = []


class LLMConversationalInterface:
    """Manages conversational flow using LLM parser"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with optional API key"""
        self.parser = LLMQueryParser(api_key=api_key)
        self.query_executor = None  # Will be imported to avoid circular dependency
        self.current_params = {}

    def set_query_executor(self, executor):
        """Set the query executor (to avoid circular imports)"""
        self.query_executor = executor

    def process_query(self, user_input: str) -> Dict[str, Any]:
        """
        Process a user query with LLM understanding

        Returns:
            Dict with status, message, clarifications, params, result
        """
        # Parse with context
        params, clarifications, explanation = self.parser.parse(
            user_input,
            context=self.current_params if self.current_params else None
        )

        # Merge with existing parameters
        self.current_params.update(params)

        # If clarifications needed
        if clarifications:
            return {
                'status': 'needs_clarification',
                'message': self._format_clarification_message(explanation, clarifications),
                'clarifications': clarifications,
                'params': self.current_params,
                'result': None
            }

        # Execute query
        if self.query_executor and self.current_params:
            result = self.query_executor.count_trials(**self.current_params)

            return {
                'status': 'executed',
                'message': self._format_result_message(result, explanation),
                'clarifications': [],
                'params': self.current_params,
                'result': result
            }

        # Need query executor
        return {
            'status': 'error',
            'message': "Query executor not configured",
            'clarifications': [],
            'params': self.current_params,
            'result': None
        }

    def _format_clarification_message(self, explanation: str, clarifications: List[str]) -> str:
        """Format clarification message"""
        msg = f"**Understanding:** {explanation}\n\n"
        msg += "**Questions:**\n"
        for i, q in enumerate(clarifications, 1):
            msg += f"{i}. {q}\n"
        return msg

    def _format_result_message(self, result: Dict[str, Any], explanation: str) -> str:
        """Format result message"""
        if not result.get('success'):
            return f"❌ Query failed: {result.get('error', 'Unknown error')}"

        msg = f"✅ **{explanation}**\n\n"
        msg += f"**Total trials found: {result['total_count']:,}**\n\n"

        if self.current_params:
            msg += "**Query parameters:**\n"
            for key, value in self.current_params.items():
                msg += f"  • {key}: {value}\n"

        return msg

    def reset(self):
        """Reset conversation"""
        self.parser.reset()
        self.current_params = {}


# MCP Tool Function using LLM parser
def mcp_llm_query(query: str, api_key: Optional[str] = None, context: Optional[Dict] = None) -> str:
    """
    MCP Tool: Natural language query using Claude LLM parser

    Args:
        query: Natural language query
        api_key: Optional Anthropic API key
        context: Optional context from previous query

    Returns:
        Formatted response string
    """
    try:
        from .query_engine import ClinicalTrialsQuery
    except ImportError:
        # Fallback for when run as script
        import sys
        sys.path.append('..')
        from query_engine import ClinicalTrialsQuery

    # Create parser and executor
    interface = LLMConversationalInterface(api_key=api_key)
    interface.set_query_executor(ClinicalTrialsQuery())

    # Process query
    response = interface.process_query(query)

    return response['message']


if __name__ == "__main__":
    # Test the LLM parser
    import sys

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        print("Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        sys.exit(1)

    print("=" * 70)
    print("LLM-BASED PARSER TEST")
    print("=" * 70)

    parser = LLMQueryParser()

    test_queries = [
        "How many interventional trials have results posted?",
        "Count completed trials without results in the United States",
        "Show me ACT trials",
        "Interventional trials for diabetes with publications",
        "Phase 2/3 trials completed in the last year",
        "Trials with FDA regulated drugs but no results posted in the US"
    ]

    for query in test_queries:
        print(f"\n{'=' * 70}")
        print(f"Query: {query}")
        print("-" * 70)

        params, clarifications, explanation = parser.parse(query)

        print(f"\nExplanation: {explanation}")
        print(f"\nParameters:")
        print(json.dumps(params, indent=2))

        if clarifications:
            print(f"\nClarifications needed:")
            for q in clarifications:
                print(f"  ? {q}")

        # Reset for next query
        parser.reset()
