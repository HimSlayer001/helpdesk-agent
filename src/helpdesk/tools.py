"""Actions the agent can take. Tickets live in SQLite so they persist between runs."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

CATEGORIES = ["access", "hardware", "software", "network", "account", "security"]
PRIORITIES = ["low", "medium", "high"]

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "create_ticket",
        "description": "Raise an IT Service Desk ticket when the knowledge base says to raise one, "
                       "or the user's problem cannot be solved by following the documented steps.",
        "parameters": {"type": "object", "required": ["category", "summary", "priority"], "properties": {
            "category": {"type": "string", "enum": CATEGORIES},
            "summary": {"type": "string", "description": "One-line description of the problem"},
            "priority": {"type": "string", "enum": PRIORITIES,
                         "description": "high for security incidents, lost devices or full outages"}}}}},
    {"type": "function", "function": {
        "name": "check_service_status",
        "description": "Check whether an IT service is up, degraded or under maintenance.",
        "parameters": {"type": "object", "required": ["service"], "properties": {
            "service": {"type": "string", "description": "e.g. vpn, email, slack, jira, github, salesforce"}}}}},
    {"type": "function", "function": {
        "name": "get_ticket",
        "description": "Look up the status of an existing ticket by its ID, e.g. IT-1001.",
        "parameters": {"type": "object", "required": ["ticket_id"], "properties": {
            "ticket_id": {"type": "string"}}}}},
]


class HelpdeskTools:
    def __init__(self, db_path: str = ":memory:", status_file: str | Path = "kb/service_status.json"):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS tickets (n INTEGER PRIMARY KEY AUTOINCREMENT, "
                        "category TEXT, summary TEXT, priority TEXT, status TEXT, created_at TEXT)")
        self.db.execute("INSERT OR IGNORE INTO sqlite_sequence(name, seq) VALUES ('tickets', 1000)")
        self.status = json.loads(Path(status_file).read_text()) if Path(status_file).exists() else {}

    def create_ticket(self, category: str, summary: str, priority: str = "medium") -> dict:
        category = category if category in CATEGORIES else "software"
        priority = priority if priority in PRIORITIES else "medium"
        cur = self.db.execute(
            "INSERT INTO tickets (category, summary, priority, status, created_at) VALUES (?,?,?,?,?)",
            (category, summary[:300], priority, "open", datetime.now(timezone.utc).isoformat()))
        self.db.commit()
        return {"ticket_id": f"IT-{cur.lastrowid}", "category": category, "priority": priority, "status": "open"}

    def get_ticket(self, ticket_id: str) -> dict:
        try:
            n = int(str(ticket_id).upper().removeprefix("IT-"))
        except ValueError:
            return {"error": f"invalid ticket id {ticket_id!r}"}
        row = self.db.execute("SELECT category, summary, priority, status FROM tickets WHERE n=?", (n,)).fetchone()
        if not row:
            return {"error": f"ticket {ticket_id} not found"}
        return dict(zip(["category", "summary", "priority", "status"], row), ticket_id=f"IT-{n}")

    def check_service_status(self, service: str) -> dict:
        key = service.strip().lower()
        if key not in self.status:
            return {"service": key, "status": "unknown", "known_services": sorted(self.status)}
        return {"service": key, **self.status[key]}

    def call(self, name: str, args: dict) -> dict:
        fn = {"create_ticket": self.create_ticket, "get_ticket": self.get_ticket,
              "check_service_status": self.check_service_status}.get(name)
        if fn is None:
            return {"error": f"unknown tool {name}"}
        try:
            return fn(**args)
        except TypeError as e:          # model sent wrong/missing arguments
            return {"error": f"bad arguments for {name}: {e}"}
