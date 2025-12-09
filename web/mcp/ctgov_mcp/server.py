#!/usr/bin/env python3
"""
ClinicalTrials.gov MCP Server Entry Point

This module provides the main entry point for the ClinicalTrials.gov MCP server.
It exposes MCP-compatible tool functions that can be integrated into any MCP server.
"""

import os
from typing import Dict, Any, Optional, List

from .interface import mcp_query_trials, mcp_structured_query
from .query_engine import ClinicalTrialsQuery


# MCP Tool Definitions
MCP_TOOLS = [
    {
        "name": "query_clinical_trials",
        "description": """Query ClinicalTrials.gov database with natural language or structured parameters.

        This tool can:
        - Count trials matching specific criteria
        - Answer questions about clinical trial statistics
        - Handle complex queries with multiple filters
        - Support both natural language and structured queries

        Examples:
        - "How many interventional trials have results?"
        - "Count ACT trials" (Applicable Clinical Trials)
        - "Trials for diabetes with publications"
        """,
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query (e.g., 'How many interventional trials have results?')"
                },
                "use_llm": {
                    "type": "boolean",
                    "description": "Use LLM-based parser for better understanding (requires ANTHROPIC_API_KEY). Default: true",
                    "default": True
                },
                # Structured parameters (alternative to natural language)
                "study_type": {
                    "type": "string",
                    "enum": ["Interventional", "Observational", "Expanded Access"],
                    "description": "Type of study"
                },
                "status": {
                    "type": "string",
                    "enum": ["com", "rec", "not", "act", "sus", "ter", "wit", "unk"],
                    "description": "Study status: com=Completed, rec=Recruiting, act=Active, etc."
                },
                "phase": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["PHASE1", "PHASE2", "PHASE3", "PHASE4", "EARLY_PHASE1", "NA"]
                    },
                    "description": "Study phases to include"
                },
                "has_results": {
                    "type": "boolean",
                    "description": "Filter by results availability (true=with results, false=without results)"
                },
                "has_publications": {
                    "type": "boolean",
                    "description": "Filter by publications in references (true=with publications, false=without)"
                },
                "fda_drug": {
                    "type": "boolean",
                    "description": "FDA regulated drug"
                },
                "fda_device": {
                    "type": "boolean",
                    "description": "FDA regulated device"
                },
                "country": {
                    "type": "string",
                    "description": "Country where trials are conducted (e.g., 'United States')"
                },
                "state": {
                    "type": "string",
                    "description": "State where trials are conducted"
                },
                "city": {
                    "type": "string",
                    "description": "City where trials are conducted"
                },
                "start_date_min": {
                    "type": "string",
                    "description": "Minimum start date (YYYY-MM-DD)"
                },
                "start_date_max": {
                    "type": "string",
                    "description": "Maximum start date (YYYY-MM-DD)"
                },
                "completion_date_min": {
                    "type": "string",
                    "description": "Minimum completion date (YYYY-MM-DD)"
                },
                "completion_date_max": {
                    "type": "string",
                    "description": "Maximum completion date (YYYY-MM-DD)"
                },
                "condition": {
                    "type": "string",
                    "description": "Disease or condition (e.g., 'diabetes', 'cancer')"
                },
                "intervention": {
                    "type": "string",
                    "description": "Treatment or intervention (e.g., 'aspirin', 'chemotherapy')"
                },
                "sponsor": {
                    "type": "string",
                    "description": "Sponsor organization name"
                },
                "keywords": {
                    "type": "string",
                    "description": "General search keywords"
                }
            },
            "anyOf": [
                {"required": ["query"]},
                {"required": ["study_type"]},
                {"required": ["condition"]},
                {"required": ["intervention"]}
            ]
        }
    }
]


def execute_tool(tool_name: str, parameters: Dict[str, Any]) -> str:
    """
    Execute an MCP tool by name

    Args:
        tool_name: Name of the tool to execute
        parameters: Tool parameters

    Returns:
        Tool execution result as string
    """
    if tool_name == "query_clinical_trials":
        # Check if this is a natural language query or structured query
        if "query" in parameters:
            query = parameters.pop("query")
            use_llm = parameters.pop("use_llm", True)

            # If there are additional structured parameters, use structured query
            if parameters:
                return mcp_structured_query(**parameters)
            else:
                return mcp_query_trials(query, use_llm=use_llm)
        else:
            # Pure structured query
            return mcp_structured_query(**parameters)

    return f"Unknown tool: {tool_name}"


def get_tool_definitions() -> List[Dict[str, Any]]:
    """
    Get MCP tool definitions for registration

    Returns:
        List of tool definition dictionaries
    """
    return MCP_TOOLS


# Direct API for non-MCP usage
class ClinicalTrialsMCPServer:
    """
    Main server class for ClinicalTrials.gov MCP integration

    Usage:
        server = ClinicalTrialsMCPServer()
        result = server.query("How many interventional trials have results?")
    """

    def __init__(self, api_key: Optional[str] = None, use_llm: bool = True):
        """
        Initialize the MCP server

        Args:
            api_key: Anthropic API key for LLM parsing (optional, uses env var if not provided)
            use_llm: Whether to use LLM-based parsing by default
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.use_llm = use_llm and bool(self.api_key)
        self.query_executor = ClinicalTrialsQuery()

    def query(self, query: str, use_llm: Optional[bool] = None) -> str:
        """
        Execute a natural language query

        Args:
            query: Natural language query
            use_llm: Override default LLM setting

        Returns:
            Formatted result string
        """
        use_llm_param = use_llm if use_llm is not None else self.use_llm
        return mcp_query_trials(query, use_llm=use_llm_param, api_key=self.api_key)

    def query_structured(self, **kwargs) -> str:
        """
        Execute a structured query with explicit parameters

        Args:
            **kwargs: Query parameters (study_type, has_results, etc.)

        Returns:
            Formatted result string
        """
        return mcp_structured_query(**kwargs)

    def get_tools(self) -> List[Dict[str, Any]]:
        """Get MCP tool definitions"""
        return get_tool_definitions()

    def execute(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """Execute a tool by name"""
        return execute_tool(tool_name, parameters)


if __name__ == "__main__":
    # Example usage
    print("=" * 70)
    print("CLINICALTRIALS.GOV MCP SERVER")
    print("=" * 70)
    print()

    server = ClinicalTrialsMCPServer()

    # Example queries
    examples = [
        "How many interventional trials have results?",
        "Count ACT trials",
        {"study_type": "Interventional", "has_results": True, "country": "United States"}
    ]

    for example in examples:
        if isinstance(example, str):
            print(f"Query: {example}")
            print("-" * 70)
            result = server.query(example)
            print(result)
        else:
            print(f"Structured query: {example}")
            print("-" * 70)
            result = server.query_structured(**example)
            print(result)
        print()
