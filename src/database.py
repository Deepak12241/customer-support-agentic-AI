import sqlite3
import os
from typing import List, Dict, Any, Optional

DB_FILE = "memory.db"

class DatabaseHelper:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Customer profile table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS customer_profile (
                    customer_id TEXT PRIMARY KEY,
                    customer_name TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Conversation logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id TEXT,
                    role TEXT,
                    message TEXT,
                    intent TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(customer_id) REFERENCES customer_profile(customer_id)
                )
            """)
            conn.commit()

    def create_or_update_profile(self, customer_id: str, customer_name: Optional[str] = None) -> str:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Check if profile exists
            cursor.execute("SELECT customer_name FROM customer_profile WHERE customer_id = ?", (customer_id,))
            row = cursor.fetchone()
            if row:
                if customer_name and row[0] != customer_name:
                    cursor.execute("UPDATE customer_profile SET customer_name = ? WHERE customer_id = ?", (customer_name, customer_id))
                    conn.commit()
                return customer_name if customer_name else row[0]
            else:
                name = customer_name if customer_name else f"Customer {customer_id}"
                cursor.execute("INSERT INTO customer_profile (customer_id, customer_name) VALUES (?, ?)", (customer_id, name))
                conn.commit()
                return name

    def get_profile(self, customer_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT customer_id, customer_name, created_at FROM customer_profile WHERE customer_id = ?", (customer_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "customer_id": row[0],
                    "customer_name": row[1],
                    "created_at": row[2]
                }
            return None

    def add_conversation_turn(self, customer_id: str, role: str, message: str, intent: Optional[str] = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO conversation_history (customer_id, role, message, intent) VALUES (?, ?, ?, ?)",
                (customer_id, role, message, intent)
            )
            conn.commit()

    def get_conversation_history(self, customer_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, message, intent, timestamp FROM conversation_history WHERE customer_id = ? ORDER BY timestamp ASC LIMIT ?",
                (customer_id, limit)
            )
            rows = cursor.fetchall()
            history = []
            for row in rows:
                history.append({
                    "role": row[0],
                    "message": row[1],
                    "intent": row[2],
                    "timestamp": row[3]
                })
            return history

    def get_last_issue(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the last customer-submitted question and its corresponding system response.
        Useful for resolving: 'What was my previous support issue?'
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Select customer messages (excluding the memory recall queries themselves if possible, or just the last non-memory customer messages)
            cursor.execute(
                """
                SELECT message, intent, id, timestamp FROM conversation_history 
                WHERE customer_id = ? AND role = 'customer' AND (intent IS NULL OR intent != 'Memory')
                ORDER BY timestamp DESC LIMIT 1
                """,
                (customer_id,)
            )
            customer_row = cursor.fetchone()
            if not customer_row:
                return None
            
            customer_msg = customer_row[0]
            customer_intent = customer_row[1]
            customer_msg_id = customer_row[2]
            
            # Find the system/agent response that came immediately after this customer message
            cursor.execute(
                """
                SELECT message, timestamp FROM conversation_history
                WHERE customer_id = ? AND role = 'agent' AND id > ?
                ORDER BY id ASC LIMIT 1
                """,
                (customer_id, customer_msg_id)
            )
            agent_row = cursor.fetchone()
            agent_msg = agent_row[0] if agent_row else "No response recorded."
            
            return {
                "customer_query": customer_msg,
                "intent": customer_intent,
                "agent_response": agent_msg
            }
