import os
import sys

# Inject src folder to system path so nested imports are resolved cleanly
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'src'))
if src_path not in sys.path:
    sys.path.append(src_path)

import sys
import os
from database import DatabaseHelper
from graph import app_graph
from agents import SupportState

def run_customer_support_system():
    db = DatabaseHelper()
    
    print("=" * 60)
    print("      ABC Technologies AI Customer Support Automation System")
    print("=" * 60)
    
    # Prompt for customer details to establish session
    customer_id = input("Enter Customer ID (e.g., CUST-1001): ").strip()
    if not customer_id:
        print("Error: Customer ID cannot be empty.")
        return
        
    customer_name = input("Enter Customer Name (optional): ").strip()
    if not customer_name:
        customer_name = None
        
    # Get existing profile details if they exist in DB
    profile = db.get_profile(customer_id)
    if profile:
        db_name = profile["customer_name"]
        print(f"\nWelcome back, {db_name}! (ID: {customer_id})")
        if not customer_name:
            customer_name = db_name
    else:
        # Create new profile
        resolved_name = db.create_or_update_profile(customer_id, customer_name)
        print(f"\nWelcome, new customer: {resolved_name}! (ID: {customer_id})")
        customer_name = resolved_name

    config = {"configurable": {"thread_id": customer_id}}
    
    print("\nSystem ready. Type 'exit' to quit the session.\n")
    
    while True:
        try:
            query = input(f"\n[{customer_name}]: ").strip()
            if not query:
                continue
            if query.lower() in ["exit", "quit", "q"]:
                print("\nThank you for using ABC Technologies customer support. Goodbye!")
                break
                
            print("\nProcessing your query...")
            
            # Initial state configuration for LangGraph
            initial_state = {
                "customer_id": customer_id,
                "customer_name": customer_name,
                "query": query,
                "intent": None,
                "history": [],
                "retrieved_context": None,
                "draft_response": None,
                "requires_approval": False,
                "approval_status": None,
                "critical_request_type": None,
                "final_response": None
            }
            
            # Run the workflow
            # Using stream to capture intermediate events
            events = app_graph.stream(initial_state, config, stream_mode="values")
            for event in events:
                # We can trace routing/steps internally if needed
                pass
                
            # Check if execution is paused for Human Approval Interrupt
            state_info = app_graph.get_state(config)
            
            if state_info.next and "human_approval" in state_info.next:
                # Retrieve current state values
                state_values = state_info.values
                critical_type = state_values.get("critical_request_type", "High-Risk Request")
                draft_resp = state_values.get("draft_response", "")
                
                print("\n" + "!" * 50)
                print("!!! [HUMAN SUPERVISOR APPROVAL REQUIRED] !!!")
                print(f"Request Type: {critical_type.upper()}")
                print(f"Customer Query: '{query}'")
                print(f"Draft Response: \n{draft_resp}")
                print("!" * 50)
                
                # Prompt human supervisor for approval
                choice = ""
                while choice not in ["y", "n", "yes", "no"]:
                    choice = input("Do you approve this request? (y/n): ").strip().lower()
                    
                status = "Approved" if choice in ["y", "yes"] else "Rejected"
                print(f"Supervisor Decision: {status}")
                
                # Update the graph state with decision, assigning it as if human_approval node did it
                app_graph.update_state(config, {"approval_status": status}, as_node="human_approval")
                
                # Resume execution
                print("Resuming workflow with supervisor decision...")
                events = app_graph.stream(None, config, stream_mode="values")
                for event in events:
                    pass
                
                # Fetch final state
                state_info = app_graph.get_state(config)
                
            # Display final agent/supervisor response
            final_state = state_info.values
            final_resp = final_state.get("final_response")
            intent = final_state.get("intent", "General")
            
            print(f"\n[Agent Routing]: {intent}")
            print(f"[Support Agent]: {final_resp}")
            
            # Log the final results in SQLite conversation history
            # Customer query
            db.add_conversation_turn(customer_id, "customer", query, intent)
            # Support response
            db.add_conversation_turn(customer_id, "agent", final_resp, intent)
            
            # Update local name in case it changed/got extracted
            if final_state.get("customer_name"):
                customer_name = final_state["customer_name"]
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    run_customer_support_system()
