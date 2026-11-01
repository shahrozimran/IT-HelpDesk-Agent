"""Open connections per operation: usable from CLI, Streamlit and tool threads."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import json
import re
import sqlite3
import uuid


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, data_dir: Path):
        self.path = Path(data_dir) / "helpdesk.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS memory (
                user_id TEXT, key TEXT, value TEXT, session_id TEXT, updated_at TEXT,
                PRIMARY KEY(user_id,key));
            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY, user_id TEXT, summary TEXT, updated_at TEXT);
            CREATE TABLE IF NOT EXISTS drafts (
                id TEXT PRIMARY KEY, user_id TEXT, session_id TEXT, summary TEXT,
                category TEXT, approved INTEGER DEFAULT 0, created_at TEXT);
            CREATE TABLE IF NOT EXISTS tickets (
                id TEXT PRIMARY KEY, draft_id TEXT UNIQUE, user_id TEXT,
                summary TEXT, category TEXT, status TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS services (
                name TEXT PRIMARY KEY, status TEXT, detail TEXT, updated_at TEXT);
            """)
            for name in ("wifi", "vpn", "printing", "accounts"):
                db.execute("INSERT OR IGNORE INTO services VALUES (?,?,?,?)",
                           (name, "operational", "Synthetic service is operating normally.", now()))

    @contextmanager
    def db(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def facts(self, user_id):
        with self.db() as db:
            return {r["key"]: r["value"] for r in db.execute(
                "SELECT key,value FROM memory WHERE user_id=?", (user_id,))}

    def save_fact(self, user_id, session_id, key, value):
        if key not in {"operating_system", "response_style", "device_type"}:
            raise ValueError("Only operating_system, response_style and device_type can be remembered.")
        if not value.strip() or len(value) > 160 or re.search(
                r"password|secret|api.?key|bearer|token|sk-", value, re.I):
            raise ValueError("Do not store credentials or oversized preferences.")
        with self.db() as db:
            db.execute("INSERT OR REPLACE INTO memory VALUES (?,?,?,?,?)",
                       (user_id, key, value.strip(), session_id, now()))
        return {"saved": True, "key": key, "value": value.strip()}

    def incidents(self, user_id):
        with self.db() as db:
            return [dict(r) for r in db.execute(
                "SELECT summary,updated_at FROM incidents WHERE user_id=? ORDER BY updated_at DESC LIMIT 5",
                (user_id,))]

    def save_incident(self, user_id, summary):
        if not summary.strip() or len(summary) > 500 or re.search(
                r"password\s*[:=]|api.?key|bearer\s|sk-", summary, re.I):
            raise ValueError("Incident summaries must be short and contain no credentials.")
        with self.db() as db:
            db.execute("INSERT INTO incidents VALUES (?,?,?,?)", (uuid.uuid4().hex, user_id, summary, now()))
        return {"saved": True, "summary": summary}

    def propose(self, user_id, session_id, summary, category):
        if category not in {"wifi", "vpn", "printing", "accounts", "other"}:
            raise ValueError("Invalid ticket category.")
        if not 5 <= len(summary.strip()) <= 500:
            raise ValueError("Ticket summaries must contain 5-500 characters.")
        # Identical repeated proposals in this session share the confirmation ID.
        with self.db() as db:
            row = db.execute("SELECT * FROM drafts WHERE user_id=? AND session_id=? AND summary=? AND category=?",
                             (user_id, session_id, summary, category)).fetchone()
            if row:
                return dict(row)
            identifier = "D-" + uuid.uuid4().hex[:12]
            db.execute("INSERT INTO drafts VALUES (?,?,?,?,?,?,?)",
                       (identifier, user_id, session_id, summary, category, 0, now()))
            return dict(db.execute("SELECT * FROM drafts WHERE id=?", (identifier,)).fetchone())

    def pending(self, user_id, session_id):
        with self.db() as db:
            return [dict(r) for r in db.execute("""SELECT d.* FROM drafts d LEFT JOIN tickets t ON t.draft_id=d.id
                WHERE d.user_id=? AND d.session_id=? AND t.id IS NULL""", (user_id, session_id))]

    def approve(self, draft_id, user_id, session_id):
        with self.db() as db:
            cursor = db.execute("UPDATE drafts SET approved=1 WHERE id=? AND user_id=? AND session_id=?",
                                (draft_id, user_id, session_id))
            if not cursor.rowcount:
                raise ValueError("Draft not found in this user's current session.")

    def create_ticket(self, draft_id, user_id, session_id):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            draft = db.execute("SELECT * FROM drafts WHERE id=? AND user_id=? AND session_id=?",
                               (draft_id, user_id, session_id)).fetchone()
            if not draft or not draft["approved"]:
                return {"error": "Human confirmation is required for this draft in its original session."}
            existing = db.execute("SELECT * FROM tickets WHERE draft_id=?", (draft_id,)).fetchone()
            if existing:
                return dict(existing)
            identifier = "HD-" + uuid.uuid4().hex[:10].upper()
            db.execute("INSERT INTO tickets VALUES (?,?,?,?,?,?,?)",
                       (identifier, draft_id, user_id, draft["summary"], draft["category"], "open", now()))
            return dict(db.execute("SELECT * FROM tickets WHERE id=?", (identifier,)).fetchone())

    def ticket(self, ticket_id, user_id):
        with self.db() as db:
            row = db.execute("SELECT * FROM tickets WHERE id=? AND user_id=?", (ticket_id, user_id)).fetchone()
            return dict(row) if row else {"error": "Ticket not found for this user."}

    def service(self, service_name):
        with self.db() as db:
            row = db.execute("SELECT * FROM services WHERE name=?", (service_name.lower(),)).fetchone()
            return ({**dict(row), "simulated": True} if row else
                    {"error": "Unknown service. Choose wifi, vpn, printing or accounts."})

    def set_service(self, service_name, status, detail):
        if status not in {"operational", "degraded", "outage"}:
            raise ValueError("Invalid status.")
        with self.db() as db:
            cursor = db.execute("UPDATE services SET status=?,detail=?,updated_at=? WHERE name=?",
                                (status, detail, now(), service_name))
            if not cursor.rowcount:
                raise ValueError("Unknown service.")


def append_event(evidence_dir: Path, event: dict):
    path = Path(evidence_dir) / "tool_calls.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"timestamp": now(), **event}, ensure_ascii=False, default=str) + "\n")
