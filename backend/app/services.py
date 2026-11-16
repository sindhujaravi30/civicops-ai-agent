import json
import sqlite3
from datetime import date, timedelta, datetime, timezone
from pathlib import Path
from typing import Any
from .settings import settings

def connect() -> sqlite3.Connection:
    """Open a SQLite connection to the configured database and ensure its folder exists."""
    path = Path(settings.database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    """Create the required citizen profile and audit tables if they are missing."""
    with connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS citizen_profiles (
            citizen_id TEXT PRIMARY KEY, full_name TEXT NOT NULL, vehicle_id TEXT NOT NULL,
            registration_status TEXT NOT NULL, insurance_expiry TEXT NOT NULL,
            outstanding_fines INTEGER NOT NULL DEFAULT 0)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, citizen_id TEXT NOT NULL,
            thread_id TEXT NOT NULL, event_type TEXT NOT NULL, details TEXT NOT NULL,
            created_at TEXT NOT NULL)""")

def seed_demo_profile() -> None:
    """Insert the default demo citizen profile used by the application UI and tests."""
    init_db()
    expiry = (date.today() + timedelta(days=10)).isoformat()
    with connect() as conn:
        conn.execute("""INSERT OR REPLACE INTO citizen_profiles
            (citizen_id, full_name, vehicle_id, registration_status, insurance_expiry, outstanding_fines)
            VALUES (?, ?, ?, ?, ?, ?)""",
            ("demo-citizen", "Demo Citizen", "AUH-12345", "expired", expiry, 0))

def get_profile(citizen_id: str) -> dict[str, Any] | None:
    """Fetch a single citizen profile by ID, returning None if it does not exist."""
    with connect() as conn:
        row = conn.execute("SELECT * FROM citizen_profiles WHERE citizen_id = ?", (citizen_id,)).fetchone()
    return dict(row) if row else None

def mock_renewal_tool(citizen_id: str, vehicle_id: str, thread_id: str) -> dict[str, Any]:
    """Simulate a registry transaction without making any external side effects."""
    return {"success": True, "simulation": True, "reference": f"SIM-{thread_id[:8].upper()}",
            "citizen_id": citizen_id, "vehicle_id": vehicle_id,
            "message": "Simulated renewal request submitted successfully."}

def write_audit(citizen_id: str, thread_id: str, event_type: str, details: dict[str, Any]) -> None:
    """Write a structured audit event for a citizen workflow run."""
    with connect() as conn:
        conn.execute("""INSERT INTO audit_events
            (citizen_id, thread_id, event_type, details, created_at) VALUES (?, ?, ?, ?, ?)""",
            (citizen_id, thread_id, event_type, json.dumps(details),
             datetime.now(timezone.utc).isoformat()))

def list_audit(citizen_id: str) -> list[dict[str, Any]]:
    """Return the most recent audit records for a citizen in reverse chronological order."""
    with connect() as conn:
        rows = conn.execute("SELECT * FROM audit_events WHERE citizen_id = ? ORDER BY id DESC LIMIT 50",
                            (citizen_id,)).fetchall()
    return [dict(row) | {"details": json.loads(row["details"])} for row in rows]
