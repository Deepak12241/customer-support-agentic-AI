from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
from typing import Dict, Any

from agents import (
    SupportState,
    intent_classifier_node,
    sales_agent_node,
    technical_agent_node,
    billing_agent_node,
    account_agent_node,
    memory_agent_node,
    supervisor_node
)

# 1. Human Approval Node
def human_approval_node(state: SupportState) -> Dict[str, Any]:
    """
    Placeholder node representing the Human-in-the-loop approval step.
    The graph is configured to interrupt BEFORE this node executes.
    When resumed, the supervisor approval choice is expected to be present in state['approval_status'].
    """
    return {}

# 2. Conditional Routing function after classification
def route_by_intent(state: SupportState) -> str:
    intent = state.get("intent")
    if intent == "Sales":
        return "sales_agent"
    elif intent == "Technical":
        return "technical_agent"
    elif intent == "Billing":
        return "billing_agent"
    elif intent == "Account":
        return "account_agent"
    elif intent == "Memory":
        return "memory_agent"
    else:
        return "sales_agent"  # Default fallback

# 3. Conditional Routing function after department agents draft a response
def route_after_agent(state: SupportState) -> str:
    if state.get("requires_approval", False):
        return "human_approval"
    else:
        return "supervisor"

# 4. Build the StateGraph
workflow = StateGraph(SupportState)

# Add Nodes
workflow.add_node("classifier", intent_classifier_node)
workflow.add_node("sales_agent", sales_agent_node)
workflow.add_node("technical_agent", technical_agent_node)
workflow.add_node("billing_agent", billing_agent_node)
workflow.add_node("account_agent", account_agent_node)
workflow.add_node("memory_agent", memory_agent_node)
workflow.add_node("human_approval", human_approval_node)
workflow.add_node("supervisor", supervisor_node)

# Set Entry Point
workflow.set_entry_point("classifier")

# Add Conditional Edges from Classifier
workflow.add_conditional_edges(
    "classifier",
    route_by_intent,
    {
        "sales_agent": "sales_agent",
        "technical_agent": "technical_agent",
        "billing_agent": "billing_agent",
        "account_agent": "account_agent",
        "memory_agent": "memory_agent"
    }
)

# Add Conditional Edges from specialized agents to check for approval requirements
workflow.add_conditional_edges(
    "sales_agent",
    route_after_agent,
    {
        "human_approval": "human_approval",
        "supervisor": "supervisor"
    }
)
workflow.add_conditional_edges(
    "technical_agent",
    route_after_agent,
    {
        "human_approval": "human_approval",
        "supervisor": "supervisor"
    }
)
workflow.add_conditional_edges(
    "billing_agent",
    route_after_agent,
    {
        "human_approval": "human_approval",
        "supervisor": "supervisor"
    }
)
workflow.add_conditional_edges(
    "account_agent",
    route_after_agent,
    {
        "human_approval": "human_approval",
        "supervisor": "supervisor"
    }
)

# Connect Memory Agent directly to END since it doesn't need Supervisor checking
workflow.add_edge("memory_agent", END)

# Connect Human Approval to Supervisor
workflow.add_edge("human_approval", "supervisor")

# Connect Supervisor to END
workflow.add_edge("supervisor", END)

# 5. Setup SQLite Checkpointer (SqliteSaver)
conn = sqlite3.connect("memory.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)

# 6. Compile the Graph
# We specify interrupt_before=["human_approval"] to pause before running the human approval block.
app_graph = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["human_approval"]
)
