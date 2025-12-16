#!/usr/bin/env python3
"""
Conversational Interface for ClinicalTrials.gov Queries

Provides an interactive chat-style interface that can ask follow-up questions
and handle natural language queries.
"""

from typing import Dict, Any, Optional
from .query_engine import ClinicalTrialsQuery
from .pattern_parser import NaturalLanguageParser, format_query_summary


class ClinicalTrialsConversation:
    """Manages conversational flow for clinical trials queries"""

    def __init__(self):
        self.parser = NaturalLanguageParser()
        self.query_executor = ClinicalTrialsQuery()
        self.conversation_history = []
        self.current_params = {}
        self.pending_clarifications = []

    def process_query(self, user_input: str) -> Dict[str, Any]:
        """
        Process a user query and return response with potential follow-up questions

        Returns:
            Dict with:
                - status: 'needs_clarification', 'ready_to_execute', 'executed'
                - message: Response message
                - clarifications: List of follow-up questions (if any)
                - params: Current query parameters
                - result: Query result (if executed)
        """
        # Store in history
        self.conversation_history.append({
            'role': 'user',
            'content': user_input
        })

        # Parse the query
        new_params, clarifications = self.parser.parse(user_input)

        # Merge with existing parameters (new params override)
        self.current_params.update(new_params)

        # Check if this is answering a previous clarification
        if self.pending_clarifications:
            self._process_clarification_answer(user_input)

        # Determine next action
        if clarifications:
            self.pending_clarifications = clarifications
            return {
                'status': 'needs_clarification',
                'message': self._format_clarification_message(),
                'clarifications': clarifications,
                'params': self.current_params,
                'result': None
            }

        # Check if we have enough to execute
        if self._can_execute():
            result = self._execute_query()
            return {
                'status': 'executed',
                'message': self._format_result_message(result),
                'clarifications': [],
                'params': self.current_params,
                'result': result
            }

        # Need more information
        return {
            'status': 'needs_clarification',
            'message': "I need more information to execute this query. What would you like to search for?",
            'clarifications': ["Please provide more details about what trials you're looking for."],
            'params': self.current_params,
            'result': None
        }

    def _process_clarification_answer(self, answer: str):
        """Process an answer to a clarification question"""
        answer_lower = answer.lower()

        # Try to extract information from the answer
        new_params, _ = self.parser.parse(answer)
        self.current_params.update(new_params)

        # Clear pending clarifications
        self.pending_clarifications = []

    def _can_execute(self) -> bool:
        """Check if we have enough information to execute a query"""
        # We can execute if we have at least one filter parameter
        # or if it's an explicit count of all trials
        return len(self.current_params) > 0

    def _execute_query(self) -> Dict[str, Any]:
        """Execute the query with current parameters"""
        result = self.query_executor.count_trials(**self.current_params)
        return result

    def _format_clarification_message(self) -> str:
        """Format message when clarification is needed"""
        msg = "I understand you're looking for clinical trials"

        if self.current_params:
            msg += " with the following criteria:\n\n"
            msg += format_query_summary(self.current_params)
            msg += "\n\n"

        msg += "However, I need some clarification:\n\n"

        for i, question in enumerate(self.pending_clarifications, 1):
            msg += f"{i}. {question}\n"

        return msg

    def _format_result_message(self, result: Dict[str, Any]) -> str:
        """Format the query result into a readable message"""
        if not result['success']:
            return f"Query failed: {result.get('error', 'Unknown error')}"

        msg = "Query executed successfully!\n\n"
        msg += f"**Total trials found: {result['total_count']:,}**\n\n"

        if self.current_params:
            msg += "Query parameters:\n"
            msg += format_query_summary(self.current_params)

        return msg

    def reset(self):
        """Reset the conversation state"""
        self.conversation_history = []
        self.current_params = {}
        self.pending_clarifications = []


def chat_interface():
    """Interactive command-line chat interface"""
    conversation = ClinicalTrialsConversation()

    print("=" * 70)
    print("CLINICALTRIALS.GOV CONVERSATIONAL QUERY INTERFACE")
    print("=" * 70)
    print("\nAsk me questions about clinical trials in natural language!")
    print("Examples:")
    print("  - How many interventional trials have results?")
    print("  - Show me completed trials without results in the US")
    print("  - Count ACT trials")
    print("  - Trials for diabetes with publications")
    print("\nType 'quit' or 'exit' to leave, 'reset' to start over.\n")

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("\nGoodbye!")
                break

            if user_input.lower() == 'reset':
                conversation.reset()
                print("\n✓ Conversation reset. Ask me a new question!\n")
                continue

            # Process the query
            response = conversation.process_query(user_input)

            # Display response
            print(f"\nAssistant: {response['message']}\n")

            # If executed, ask if they want to refine or start new query
            if response['status'] == 'executed':
                print("Would you like to refine this query or ask something new?\n")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


# MCP-style function that uses the conversational interface
def mcp_natural_language_query(query: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    MCP Tool: Natural language query for clinical trials

    This tool accepts natural language queries and returns results,
    asking follow-up questions when needed.

    Args:
        query: Natural language query (e.g., "How many interventional trials have results?")
        context: Optional context from previous queries (params to continue with)

    Returns:
        Formatted response string with results or clarification questions
    """
    conversation = ClinicalTrialsConversation()

    # If context provided, use it
    if context:
        conversation.current_params = context

    response = conversation.process_query(query)

    output = response['message']

    # Add context info if there are pending clarifications
    if response['status'] == 'needs_clarification':
        output += "\n\n(Provide answers to these questions to continue the query)"

    return output


def mcp_execute_structured_query(**kwargs) -> str:
    """
    MCP Tool: Execute a structured query with explicit parameters

    This is an alternative to natural language queries where you specify
    parameters directly.

    Args:
        Same as ClinicalTrialsQuery.count_trials()

    Returns:
        Formatted result string
    """
    query = ClinicalTrialsQuery()
    result = query.count_trials(**kwargs)

    if result['success']:
        output = f"Total trials found: {result['total_count']:,}\n\n"
        output += "Filters applied:\n"
        output += format_query_summary(kwargs)
        return output
    else:
        return f"Query failed: {result.get('error', 'Unknown error')}"


if __name__ == "__main__":
    # Run the interactive chat interface
    chat_interface()
