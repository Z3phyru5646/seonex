"""Small local SQLite store for reviewer decisions, labels and snapshots."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path("data/seonex.db")


def _connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS intent_overrides (url TEXT PRIMARY KEY, intent TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS reviews (pair_key TEXT PRIMARY KEY, decision TEXT NOT NULL, note TEXT, preferred_url TEXT, implemented INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS labels (pair_key TEXT PRIMARY KEY, label TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, base_url TEXT NOT NULL, payload TEXT NOT NULL);
    """)
    return connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_intent_overrides() -> dict[str, str]:
    with _connection() as con:
        return {row["url"]: row["intent"] for row in con.execute("SELECT url, intent FROM intent_overrides")}


def save_intent_override(url: str, intent: str) -> None:
    with _connection() as con:
        con.execute("INSERT INTO intent_overrides(url,intent,updated_at) VALUES(?,?,?) ON CONFLICT(url) DO UPDATE SET intent=excluded.intent,updated_at=excluded.updated_at", (url, intent, _now()))


def pair_key(first: str, second: str) -> str:
    return "|".join(sorted((first, second)))


def get_reviews() -> dict[str, dict]:
    with _connection() as con:
        return {row["pair_key"]: dict(row) for row in con.execute("SELECT * FROM reviews")}


def save_review(first: str, second: str, decision: str, note: str, preferred_url: str, implemented: bool) -> None:
    with _connection() as con:
        con.execute("""INSERT INTO reviews(pair_key,decision,note,preferred_url,implemented,updated_at)
        VALUES(?,?,?,?,?,?) ON CONFLICT(pair_key) DO UPDATE SET decision=excluded.decision,note=excluded.note,
        preferred_url=excluded.preferred_url,implemented=excluded.implemented,updated_at=excluded.updated_at""",
        (pair_key(first, second), decision, note, preferred_url, int(implemented), _now()))


def save_label(first: str, second: str, label: str) -> None:
    with _connection() as con:
        con.execute("INSERT INTO labels(pair_key,label,updated_at) VALUES(?,?,?) ON CONFLICT(pair_key) DO UPDATE SET label=excluded.label,updated_at=excluded.updated_at", (pair_key(first, second), label, _now()))


def get_labels() -> dict[str, str]:
    with _connection() as con:
        return {row["pair_key"]: row["label"] for row in con.execute("SELECT pair_key,label FROM labels")}


def save_snapshot(base_url: str, pages: list[dict], conflicts: list[dict]) -> int:
    payload = json.dumps({"pages": pages, "conflicts": conflicts})
    with _connection() as con:
        cursor = con.execute("INSERT INTO snapshots(created_at,base_url,payload) VALUES(?,?,?)", (_now(), base_url, payload))
        return int(cursor.lastrowid)


def list_snapshots() -> list[dict]:
    with _connection() as con:
        return [dict(row) for row in con.execute("SELECT id,created_at,base_url FROM snapshots ORDER BY id DESC")]


def load_snapshot(snapshot_id: int) -> dict:
    with _connection() as con:
        row = con.execute("SELECT * FROM snapshots WHERE id=?", (snapshot_id,)).fetchone()
    if row is None:
        raise ValueError("Snapshot not found")
    data = dict(row)
    data["payload"] = json.loads(data["payload"])
    return data
