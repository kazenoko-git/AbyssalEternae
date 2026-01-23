import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[3] / "music_cache.db"

class MusicDB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self._init()

    def _init(self):
        cur = self.conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS music (
            hash TEXT PRIMARY KEY,
            plan TEXT,
            path TEXT
        )
        """)
        self.conn.commit()

    def get(self, key):
        cur = self.conn.cursor()
        cur.execute("SELECT plan, path FROM music WHERE hash=?", (key,))
        return cur.fetchone()

    def save(self, key, plan_json, path):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO music VALUES (?, ?, ?)",
            (key, plan_json, str(path))
        )
        self.conn.commit()
