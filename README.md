# AI-Powered Customer Support Automation System

An intelligent, multi-agent customer support automation system built with **LangGraph**, **SQLite**, and **Ollama (Llama 3.1)**. 

The system automates ticket classification, routes queries to specialized support departments, retrieves context from a local knowledge base (RAG), tracks customer interaction history (SQLite memory), enforces human supervisor approvals for high-risk requests (Human-in-the-Loop), and validates draft responses via a Supervisor agent.

---

## 1. Project Structure

- `knowledge_base/` - Directory containing text documents used for RAG context.
  - `company_policy.txt` - Guidelines for refunds, cancellations, and escalations.
  - `pricing_guide.txt` - Pricing details, features, and plans.
  - `technical_manual.txt` - System requirements and troubleshooting guides.
  - `faq_document.txt` - General FAQs (password reset, account status, etc.).
- `database.py` - Manages customer profiles, logs conversation history, and handles SQLite queries in `memory.db`.
- `rag.py` - Core search and retrieval engine using TF-IDF vectorization.
- `agents.py` - Implements the state structure, LLM interactions, intent classifier, support agents, and supervisor node.
- `graph.py` - Orchestrates the StateGraph workflow, routing logic, and checkpoint configuration.
- `app.py` - Interactive Command Line Interface (CLI) for customer interactions.
- `run_demo.py` - Mock script simulating standard interaction flows against all 5 sample queries.
- `generate_diagram.py` - Generates a Mermaid workflow structure and draws `workflow.png`.
- `memory.db` - SQLite database containing conversation logs and checkpoint savers.
- `workflow.png` - Rendered LangGraph workflow architecture.
- `workflow.mermaid` - Mermaid source code of the workflow diagram.
- `demo_output.log` - Transcript log of the demo run.

---

## 2. Prerequisites & Setup

### Requirements
- **Python**: 3.10 or later (Tested on 3.14.0)
- **Ollama**: Installed and running locally
- **Llama 3.1 Model**: Pulled in Ollama (`ollama pull llama3.1`)
- **Python Packages**: `langgraph`, `langgraph-checkpoint-sqlite`, `langchain-ollama`, `scikit-learn`, `numpy` (Already configured in the workspace)

### Installation
If running on a fresh environment, run:
```bash
pip install langgraph langgraph-checkpoint-sqlite langchain-ollama scikit-learn numpy
```

Ensure Ollama is running:
```bash
ollama run llama3.1
```

---

## 3. How to Run

### Run Interactive Support CLI (Preferred)
To run the interactive customer support terminal, execute:
```bash
python app.py
```
* **Step 1**: Enter a unique Customer ID (e.g., `CUST-1001`). If you have a profile, it will welcome you back.
* **Step 2**: Enter Customer Name (optional).
* **Step 3**: Start chatting! Type queries like:
  - *What pricing plans are available?*
  - *My app crashes on uploading a file.*
  - *I forgot my password.*
  - *I need a refund for my annual subscription.* (This will trigger a supervisor approval prompt in the console).
  - *What was my previous support issue?* (Recalls the last query/response from SQLite history).
* **Step 4**: Type `exit` to quit.

### Run Automated Demo Execution
To execute a simulated interactive run containing all 5 assignment queries and outputting a full execution transcript, run:
```bash
python run_demo.py
```
This generates `demo_output.log` showing the exact inputs, agent routing paths, RAG sources, and supervisor outputs.

### Re-Generate Architecture Diagram
To update the Mermaid script and PNG flow diagram, execute:
```bash
python generate_diagram.py
```

---

## 4. SQLite Memory Database Schema

The database `memory.db` utilizes two custom tables:

### customer_profile
Stores unique profiles for each customer:
- `customer_id` (TEXT, Primary Key)
- `customer_name` (TEXT)
- `created_at` (DATETIME)

### conversation_history
Logs every customer query and agent response for conversational memory recall:
- `id` (INTEGER, Primary Key, Auto-increment)
- `customer_id` (TEXT, Foreign Key)
- `role` (TEXT: 'customer' or 'agent')
- `message` (TEXT)
- `intent` (TEXT: 'Sales', 'Technical', 'Billing', 'Account', 'Memory')
- `timestamp` (DATETIME)

Additionally, LangGraph uses `SqliteSaver` to automatically maintain internal node checkpoints and state histories under system-defined tables in the same `memory.db`.
