import sqlite3
import time
from pathlib import Path

from core.config import get_config


class MemoryStore:
    def __init__(self):
        cfg = get_config()["memory"]
        self.db_path = Path(cfg["db_path"])
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS facts (key TEXT PRIMARY KEY, value TEXT, ts REAL)"
        )
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS history ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, content TEXT, ts REAL)"
        )
        self.conn.commit()

    def add_fact(self, key, value):
        self.conn.execute(
            "REPLACE INTO facts(key, value, ts) VALUES(?, ?, ?)",
            (key, value, time.time()),
        )
        self.conn.commit()

    def get_fact(self, key):
        r = self.conn.execute(
            "SELECT value FROM facts WHERE key=?", (key,)
        ).fetchone()
        return r[0] if r else None

    def search_facts(self, query):
        like = f"%{query}%"
        return self.conn.execute(
            "SELECT key, value FROM facts WHERE key LIKE ? OR value LIKE ?",
            (like, like),
        ).fetchall()

    def recent_facts(self, limit=8):
        return self.conn.execute(
            "SELECT key, value FROM facts ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()

    def add_message(self, role, content):
        self.conn.execute(
            "INSERT INTO history(role, content, ts) VALUES(?, ?, ?)",
            (role, content, time.time()),
        )
        self.conn.commit()

    def close(self):
        self.conn.close()
