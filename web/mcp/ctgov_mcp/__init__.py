"""
ClinicalTrials.gov MCP Server Package

A comprehensive MCP-style interface for querying ClinicalTrials.gov with
natural language support using LLM or pattern-based parsing.
"""

from .query_engine import (
    ClinicalTrialsQuery,
    ClinicalTrialsQueryBuilder,
    mcp_count_trials,
    mcp_get_trial_details,
)

from .interface import (
    UnifiedQueryInterface,
    mcp_query_trials,
    mcp_structured_query,
    single_query,
)

from .server import (
    ClinicalTrialsMCPServer,
    get_tool_definitions,
    execute_tool,
)

# Optional LLM parser (requires anthropic package and API key)
try:
    from .llm_parser import (
        LLMQueryParser,
        LLMConversationalInterface,
        mcp_llm_query,
    )
    HAS_LLM_PARSER = True
except ImportError:
    HAS_LLM_PARSER = False

# Optional pattern parser
try:
    from .pattern_parser import (
        NaturalLanguageParser,
        format_query_summary,
    )
    HAS_PATTERN_PARSER = True
except ImportError:
    HAS_PATTERN_PARSER = False


__version__ = "1.0.0"
__author__ = "ClinicalTrials MCP Team"

__all__ = [
    # Core query engine
    "ClinicalTrialsQuery",
    "ClinicalTrialsQueryBuilder",

    # MCP Server
    "ClinicalTrialsMCPServer",
    "get_tool_definitions",
    "execute_tool",

    # Unified interface
    "UnifiedQueryInterface",
    "single_query",

    # MCP tool functions
    "mcp_query_trials",
    "mcp_structured_query",
    "mcp_count_trials",
    "mcp_get_trial_details",

    # Optional exports
    "HAS_LLM_PARSER",
    "HAS_PATTERN_PARSER",
]

# Add LLM exports if available
if HAS_LLM_PARSER:
    __all__.extend([
        "LLMQueryParser",
        "LLMConversationalInterface",
        "mcp_llm_query",
    ])

# Add pattern parser exports if available
if HAS_PATTERN_PARSER:
    __all__.extend([
        "NaturalLanguageParser",
        "format_query_summary",
    ])
