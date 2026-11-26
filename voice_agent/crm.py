"""Tiny SQLite CRM: leads, conversations and appointments.

SQLite keeps the demo fully local and free while still demonstrating the
integration pattern (write lead on qualification, write appointment on booking).
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import date, timedelta
from typing import Dict, List

from .config import DB_PATH

_LOCK = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    name TEXT, company TEXT, role TEXT, need TEXT,
    budget INTEGER, timeline TEXT, authority TEXT,
    score INTEGER, grade TEXT, sentiment TEXT, language TEXT,
    status TEXT DEFAULT 'NEW',
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    appt_date TEXT NOT NULL,
    appt_time TEXT NOT NULL,
    purpose TEXT,
    status TEXT DEFAULT 'CONFIRMED',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (lead_id) REFERENCES leads(id)
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    text TEXT NOT NULL,
    language TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS call_summaries (
    session_id TEXT PRIMARY KEY,
    summary TEXT NOT NULL,
    insights TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _LOCK, _connect() as conn:
        conn.executescript(SCHEMA)


def save_message(session_id: str, role: str, text: str, language: str = "") -> None:
    with _LOCK, _connect() as conn:
        conn.execute("INSERT INTO messages (session_id, role, text, language) VALUES (?,?,?,?)",
                     (session_id, role, text, language))


def get_messages(session_id: str) -> List[Dict]:
    with _LOCK, _connect() as conn:
        rows = conn.execute("SELECT role, text, language, created_at FROM messages WHERE session_id=? ORDER BY id",
                            (session_id,)).fetchall()
    return [dict(r) for r in rows]


def upsert_lead(session_id: str, slots: Dict[str, object], score: Dict[str, object],
                sentiment: str, language: str) -> int:
    with _LOCK, _connect() as conn:
        conn.execute(
            """INSERT INTO leads (session_id, name, company, role, need, budget, timeline,
                                  authority, score, grade, sentiment, language)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(session_id) DO UPDATE SET
                 name=excluded.name, company=excluded.company, role=excluded.role,
                 need=excluded.need, budget=excluded.budget, timeline=excluded.timeline,
                 authority=excluded.authority, score=excluded.score, grade=excluded.grade,
                 sentiment=excluded.sentiment, language=excluded.language""",
            (session_id, slots.get("name"), slots.get("company"), slots.get("role"),
             slots.get("need"), slots.get("budget_value"), slots.get("timeline_text"),
             slots.get("authority"), score["total"], score["grade"], sentiment, language),
        )
        row = conn.execute("SELECT id FROM leads WHERE session_id=?", (session_id,)).fetchone()
    return int(row["id"])


def book_appointment(lead_id: int, appt_date: str, appt_time: str, purpose: str = "Product demo") -> Dict:
    with _LOCK, _connect() as conn:
        exists = conn.execute(
            "SELECT id FROM appointments WHERE appt_date=? AND appt_time=? AND status='CONFIRMED'",
            (appt_date, appt_time)).fetchone()
        if exists:
            return {"ok": False, "reason": "That slot is already taken."}
        cur = conn.execute(
            "INSERT INTO appointments (lead_id, appt_date, appt_time, purpose) VALUES (?,?,?,?)",
            (lead_id, appt_date, appt_time, purpose))
        conn.execute("UPDATE leads SET status='APPOINTMENT' WHERE id=?", (lead_id,))
        appt_id = cur.lastrowid
    return {"ok": True, "id": appt_id, "date": appt_date, "time": appt_time, "purpose": purpose}


def list_available_slots(days_ahead: int = 5) -> List[Dict[str, str]]:
    """Return free 30-minute business-hour slots for the next few days."""
    with _LOCK, _connect() as conn:
        taken = {f"{r['appt_date']}|{r['appt_time']}" for r in conn.execute(
            "SELECT appt_date, appt_time FROM appointments WHERE status='CONFIRMED'")}
    slots: List[Dict[str, str]] = []
    today = date.today()
    offset = 1
    while len({s["date"] for s in slots}) < 3 and offset <= days_ahead:
        day = today + timedelta(days=offset)
        offset += 1
        if day.weekday() >= 5:
            continue
        for hour in (10, 11, 14, 15, 16):
            for minute in (0, 30):
                label = f"{hour:02d}:{minute:02d}"
                if f"{day.isoformat()}|{label}" not in taken:
                    slots.append({"date": day.isoformat(), "time": label})
    return slots[:12]


def list_leads() -> List[Dict]:
    with _LOCK, _connect() as conn:
        rows = conn.execute(
            """SELECT l.*, (SELECT COUNT(*) FROM appointments a WHERE a.lead_id=l.id) AS appointments
               FROM leads l ORDER BY l.id DESC LIMIT 25""").fetchall()
    return [dict(r) for r in rows]


def save_summary(session_id: str, summary: str, insights: str) -> None:
    with _LOCK, _connect() as conn:
        conn.execute(
            """INSERT INTO call_summaries (session_id, summary, insights) VALUES (?,?,?)
               ON CONFLICT(session_id) DO UPDATE SET summary=excluded.summary, insights=excluded.insights""",
            (session_id, summary, insights))


def get_summary(session_id: str) -> Dict | None:
    with _LOCK, _connect() as conn:
        row = conn.execute("SELECT * FROM call_summaries WHERE session_id=?", (session_id,)).fetchone()
    return dict(row) if row else None


def reset_demo_data() -> None:
    with _LOCK, _connect() as conn:
        for table in ("call_summaries", "messages", "appointments", "leads"):
            conn.execute(f"DELETE FROM {table}")
