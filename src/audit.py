"""Journal d'audit (traçabilité) : chaque décision et chaque action est écrite en SQLite."""
import json
import sqlite3
from pathlib import Path

from .config import get_settings
from .schemas import now_iso


def _conn() -> sqlite3.Connection:
    path = Path(get_settings().audit_db)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, "
        "incident_id TEXT, actor TEXT, event TEXT, details TEXT)"
    )
    return conn


def log_event(incident_id: str, actor: str, event: str, details: dict | None = None) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO audit (ts, incident_id, actor, event, details) VALUES (?,?,?,?,?)",
            (now_iso(), incident_id, actor, event, json.dumps(details or {}, ensure_ascii=False)),
        )


def list_events(limit: int = 100) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT ts, incident_id, actor, event, details FROM audit ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {"ts": r[0], "incident_id": r[1], "actor": r[2], "event": r[3], "details": json.loads(r[4])}
        for r in rows
    ]
