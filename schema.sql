-- Database Schema for Customer Support Automation System
-- Re-create this schema by running in SQLite: sqlite3 memory.db < schema.sql

CREATE TABLE IF NOT EXISTS customer_profile (
    customer_id TEXT PRIMARY KEY,
    customer_name TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT,
    role TEXT, -- 'customer' | 'agent' | 'supervisor'
    message TEXT,
    intent TEXT, -- 'Sales' | 'Technical' | 'Billing' | 'Account' | 'Memory'
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(customer_id) REFERENCES customer_profile(customer_id)
);
