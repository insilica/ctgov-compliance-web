#!/usr/bin/env python3
"""
Unified ClinicalTrials.gov Query Interface

Supports both pattern-based and LLM-based natural language parsing.
"""

import os
import sys
from typing import Dict, Any, Optional
from .query_engine import ClinicalTrialsQuery


class UnifiedQueryInterface:
    """
    Unified interface that can use either pattern-based or LLM-based parsing
    """

    def __init__(self, use_llm: bool = True, api_key: Optional[str] = None):
        """
        Initialize the interface

        Args:
            use_llm: If True, use LLM-based parser (requires API key)
                    If False, use pattern-based parser
            api_key: Anthropic API key (for LLM mode)
        """
        self.use_llm = use_llm
        self.query_executor = ClinicalTrialsQuery()
        self.current_params = {}
        self.conversation_history = []

        if use_llm:
            # Try to import and initialize LLM parser
            try:
                from .llm_parser import LLMConversationalInterface
                self.interface = LLMConversationalInterface(api_key=api_key)
                self.interface.set_query_executor(self.query_executor)
                print("✓ Using LLM-based parser (Claude)")
            except ImportError as e:
                print(f"✗ Failed to import LLM parser: {e}")
                print("  Falling back to pattern-based parser")
                self.use_llm = False
            except ValueError as e:
                print(f"✗ LLM parser error: {e}")
                print("  Falling back to pattern-based parser")
                self.use_llm = False

        if not use_llm:
            # Use pattern-based parser
            from .chat import ClinicalTrialsConversation
            self.interface = ClinicalTrialsConversation()
            print("✓ Using pattern-based parser")

    def process_query(self, user_input: str) -> Dict[str, Any]:
        """Process a query using the configured parser"""
        return self.interface.process_query(user_input)

    def reset(self):
        """Reset the conversation"""
        self.interface.reset()
        self.current_params = {}
        self.conversation_history = []


def interactive_chat(use_llm: bool = True):
    """
    Interactive chat interface

    Args:
        use_llm: Use LLM-based parser if True, pattern-based if False
    """
    print("=" * 70)
    print("CLINICALTRIALS.GOV UNIFIED QUERY INTERFACE")
    print("=" * 70)
    print()

    # Initialize interface
    try:
        interface = UnifiedQueryInterface(use_llm=use_llm)
    except Exception as e:
        print(f"✗ Failed to initialize interface: {e}")
        return

    print()
    print("Ask me questions about clinical trials in natural language!")
    print()
    print("Examples:")
    print("  • How many interventional trials have results?")
    print("  • Show me completed trials without results in the US")
    print("  • Count ACT trials")
    print("  • Trials for diabetes with publications")
    print("  • Phase 2/3 FDA drug trials completed last year")
    print()
    print("Commands:")
    print("  • 'quit' or 'exit' - Exit the program")
    print("  • 'reset' - Start a new conversation")
    print("  • 'switch' - Switch between LLM and pattern-based parsing")
    print()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', 'bye', 'q']:
                print("\nGoodbye!")
                break

            if user_input.lower() in ['reset', 'clear', 'new']:
                interface.reset()
                print("\n✓ Conversation reset. Ask me a new question!\n")
                continue

            if user_input.lower() in ['switch', 'toggle']:
                interface = UnifiedQueryInterface(use_llm=not interface.use_llm)
                print()
                continue

            # Process query
            response = interface.process_query(user_input)

            # Display response
            print(f"\nAssistant:\n{response['message']}\n")

            # Show parameter summary if executed
            if response['status'] == 'executed' and response.get('params'):
                print("(You can refine this query or ask something new)\n")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\n✗ Error: {e}\n")
            import traceback
            traceback.print_exc()


def single_query(query: str, use_llm: bool = True) -> Dict[str, Any]:
    """
    Execute a single query and return results

    Args:
        query: Natural language query
        use_llm: Use LLM parser if True

    Returns:
        Response dictionary
    """
    interface = UnifiedQueryInterface(use_llm=use_llm)
    return interface.process_query(query)


# MCP Tool Functions
def mcp_query_trials(query: str, use_llm: bool = True, api_key: Optional[str] = None) -> str:
    """
    MCP Tool: Query clinical trials with natural language

    Args:
        query: Natural language query
        use_llm: Use LLM-based parser (default True)
        api_key: Anthropic API key (for LLM mode)

    Returns:
        Formatted response string
    """
    try:
        interface = UnifiedQueryInterface(use_llm=use_llm, api_key=api_key)
        response = interface.process_query(query)
        return response['message']
    except Exception as e:
        return f"✗ Error: {str(e)}"


def mcp_structured_query(**kwargs) -> str:
    """
    MCP Tool: Direct structured query (no parsing needed)

    Accepts any ClinicalTrials.gov API parameters directly.

    Returns:
        Formatted response string
    """
    from .query_engine import mcp_count_trials
    return mcp_count_trials(**kwargs)


if __name__ == "__main__":
    # Parse command line arguments
    use_llm = True

    if len(sys.argv) > 1:
        if sys.argv[1] in ['--pattern', '--no-llm', '-p']:
            use_llm = False
        elif sys.argv[1] in ['--llm', '-l']:
            use_llm = True
        elif sys.argv[1] in ['--help', '-h']:
            print("Usage: python3 clinical_trials_unified.py [OPTIONS]")
            print()
            print("Options:")
            print("  --llm, -l        Use LLM-based parser (default)")
            print("  --pattern, -p    Use pattern-based parser")
            print("  --help, -h       Show this help message")
            print()
            print("Environment Variables:")
            print("  ANTHROPIC_API_KEY   Required for LLM-based parsing")
            sys.exit(0)

    # Check for API key if using LLM
    if use_llm and not os.getenv("ANTHROPIC_API_KEY"):
        print("Warning: ANTHROPIC_API_KEY not set. Will fall back to pattern-based parsing.")
        print("To use LLM parsing, set your API key:")
        print("  export ANTHROPIC_API_KEY='your-key-here'")
        print()

    # Run interactive chat
    interactive_chat(use_llm=use_llm)
