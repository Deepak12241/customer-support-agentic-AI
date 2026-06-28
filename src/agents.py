from typing import TypedDict, List, Dict, Any, Optional
import json
import re
from langchain_ollama import ChatOllama
from database import DatabaseHelper
from rag import RAGRetriever

# 1. State Definition
class SupportState(TypedDict):
    customer_id: str
    customer_name: Optional[str]
    query: str
    intent: Optional[str]
    history: List[Dict[str, str]]
    retrieved_context: Optional[str]
    draft_response: Optional[str]
    requires_approval: bool
    approval_status: Optional[str]  # 'Pending', 'Approved', 'Rejected'
    critical_request_type: Optional[str]  # 'refund', 'cancellation', 'closure', 'compensation', 'escalation'
    final_response: Optional[str]

# Initialize LLM
llm = ChatOllama(model="llama3.1:latest", temperature=0)
db = DatabaseHelper()
retriever = RAGRetriever()

# Helper function to extract JSON from LLM output safely
def parse_json_response(text: str) -> dict:
    try:
        # Find first '{' and last '}'
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            json_str = text[start:end+1]
            return json.loads(json_str)
    except Exception as e:
        print(f"Error parsing JSON from LLM output: {e}")
    return {}

# 2. Intent Classifier Node
def intent_classifier_node(state: SupportState) -> Dict[str, Any]:
    query = state["query"]
    
    prompt = f"""You are an expert Intent Classifier and Name Extractor for a SaaS Customer Support system.
Analyze the customer's query and extract:
1. The primary intent. Choose EXACTLY ONE from:
   - "Sales": For queries about pricing, plans, costs, billing intervals, or software features.
   - "Technical": For queries about bugs, crashes, errors (e.g. file upload crashing), installation, ports, or setup issues.
   - "Billing": For invoice requests, credit card updates, payments, refunds, or compensation requests.
   - "Account": For password resets, profile settings, account deactivation/activation, account closure, or subscription cancellation.
   - "Memory": If the user is specifically asking about their previous interactions, name, past issues, or history (e.g., "What was my previous issue?", "Do you remember my name?", "What did I ask you before?").
2. The customer's name if they introduce themselves (e.g., "My name is David" -> "David", "I am Alice" -> "Alice"). If not mentioned, set to null.

Format your response as a strict JSON object:
{{
  "intent": "Sales" | "Technical" | "Billing" | "Account" | "Memory",
  "customer_name": "extracted_name" or null
}}

Do not include any preambles, explanations, or backticks. Return ONLY the JSON object.

Customer Query: "{query}"
"""
    
    response = llm.invoke(prompt)
    data = parse_json_response(response.content)
    
    intent = data.get("intent", "Sales")
    extracted_name = data.get("customer_name")
    
    # Save the profile name to database if extracted
    current_name = state.get("customer_name")
    if extracted_name:
        current_name = db.create_or_update_profile(state["customer_id"], extracted_name)
    else:
        current_name = db.create_or_update_profile(state["customer_id"], current_name)

    return {
        "intent": intent,
        "customer_name": current_name
    }

# 3. Sales Support Agent Node
def sales_agent_node(state: SupportState) -> Dict[str, Any]:
    query = state["query"]
    # Retrieve documents
    context = retriever.retrieve(query)
    
    prompt = f"""You are an expert Sales Support Agent for ABC Technologies.
Your job is to answer product questions, pricing plans, and subscription details.
Use the retrieved company information below to draft a helpful, professional response.

Retrieved Context:
{context}

Customer Query: {query}

Draft a clear response highlighting the plans, pricing, or features requested.
"""
    response = llm.invoke(prompt)
    return {
        "retrieved_context": context,
        "draft_response": response.content,
        "requires_approval": False
    }

# 4. Technical Support Agent Node
def technical_agent_node(state: SupportState) -> Dict[str, Any]:
    query = state["query"]
    context = retriever.retrieve(query)
    
    prompt = f"""You are an expert Technical Support Agent for ABC Technologies.
Your job is to solve application errors, installation problems, crashes, or configurations.
Use the retrieved technical manual content below to provide step-by-step troubleshooting.

Retrieved Context:
{context}

Customer Query: {query}

Draft a clear, step-by-step response to troubleshoot and solve the user's issue.
"""
    response = llm.invoke(prompt)
    return {
        "retrieved_context": context,
        "draft_response": response.content,
        "requires_approval": False
    }

# 5. Billing Support Agent Node
def billing_agent_node(state: SupportState) -> Dict[str, Any]:
    query = state["query"]
    context = retriever.retrieve(query)
    
    # Check for high-risk requests
    query_lower = query.lower()
    requires_approval = False
    critical_type = None
    
    if "refund" in query_lower:
        requires_approval = True
        critical_type = "refund"
    elif "compensation" in query_lower or "credit" in query_lower:
        requires_approval = True
        critical_type = "compensation"
    
    prompt = f"""You are an expert Billing Support Agent for ABC Technologies.
Your job is to answer questions about invoices, payments, and billing details.
Use the retrieved context below to draft a response.

Retrieved Context:
{context}

Customer Query: {query}
"""
    if requires_approval:
        prompt += f"\nNote: The user is asking for a {critical_type}. This is a high-risk request. Draft a polite response informing them that their request has been submitted to a human supervisor for approval, and we will get back to them immediately."
    else:
        prompt += "\nDraft a helpful response resolving their query."
        
    response = llm.invoke(prompt)
    return {
        "retrieved_context": context,
        "draft_response": response.content,
        "requires_approval": requires_approval,
        "critical_request_type": critical_type
    }

# 6. Account Support Agent Node
def account_agent_node(state: SupportState) -> Dict[str, Any]:
    query = state["query"]
    context = retriever.retrieve(query)
    
    query_lower = query.lower()
    requires_approval = False
    critical_type = None
    
    if "cancel" in query_lower and "subscription" in query_lower:
        requires_approval = True
        critical_type = "cancellation"
    elif "close" in query_lower and "account" in query_lower:
        requires_approval = True
        critical_type = "closure"
    elif "escalat" in query_lower and ("management" in query_lower or "manager" in query_lower or "supervisor" in query_lower):
        requires_approval = True
        critical_type = "escalation"

    prompt = f"""You are an expert Account Support Agent for ABC Technologies.
Your job is to assist with password resets, profile settings, account status, and subscription changes.
Use the retrieved context below to draft a response.

Retrieved Context:
{context}

Customer Query: {query}
"""
    if requires_approval:
        prompt += f"\nNote: The user is asking for {critical_type}. This requires human supervisor approval. Draft a response stating that their request has been logged and escalated to a human supervisor for review."
    else:
        prompt += "\nDraft a helpful response resolving their query."
        
    response = llm.invoke(prompt)
    return {
        "retrieved_context": context,
        "draft_response": response.content,
        "requires_approval": requires_approval,
        "critical_request_type": critical_type
    }

# 7. Memory Agent Node
def memory_agent_node(state: SupportState) -> Dict[str, Any]:
    customer_id = state["customer_id"]
    last_issue = db.get_last_issue(customer_id)
    
    if last_issue:
        response_text = f"Based on your profile history, your previous support issue was:\n" \
                        f"Query: \"{last_issue['customer_query']}\" (Category: {last_issue['intent']})\n\n" \
                        f"The response provided was:\n" \
                        f"\"{last_issue['agent_response']}\""
    else:
        response_text = f"Hello {state.get('customer_name', 'there')}, I searched my database but couldn't find any previous support issues in your history. How can I help you today?"
        
    return {
        "final_response": response_text,
        "requires_approval": False
    }

# 8. Supervisor Agent Node
def supervisor_node(state: SupportState) -> Dict[str, Any]:
    query = state["query"]
    draft = state["draft_response"]
    context = state["retrieved_context"]
    approval_status = state.get("approval_status")
    critical_type = state.get("critical_request_type")
    
    if state["requires_approval"]:
        if approval_status == "Approved":
            prompt = f"""You are a Supervisor Agent. A critical request ({critical_type}) was APPROVED by a human supervisor.
Review the initial draft, and write the final response to the customer confirming the approval and explaining the next steps based on the company policy context below.

Policy Context:
{context}

Customer Query: {query}
Draft Response: {draft}

Generate the final approved message. Maintain a highly professional and polite tone.
"""
        else:  # Rejected
            prompt = f"""You are a Supervisor Agent. A critical request ({critical_type}) was REJECTED by a human supervisor.
Write a polite, professional rejection message explaining why the request could not be fulfilled based on the policy context below. Do not be hostile.

Policy Context:
{context}

Customer Query: {query}
Draft Response: {draft}

Generate the final polite rejection message.
"""
    else:
        # Standard validation and polish
        prompt = f"""You are a Supervisor Agent. Validate and improve this draft response to a customer.
Ensure:
1. It is fully accurate based on the retrieved context.
2. It maintains a polite, professional, and clear tone.
3. It resolves the customer's query.

Retrieved Context:
{context}

Customer Query: {query}
Draft Response: {draft}

Output the final, polished response for the customer. Do not include any meta-text, introductions like 'Here is the response:', or quotes around it.
"""
    
    response = llm.invoke(prompt)
    return {
        "final_response": response.content.strip()
    }
