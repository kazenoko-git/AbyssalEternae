import sqlite3
import json


class ChunkCache:

    def __init__(self):

        self.Conn = sqlite3.connect("world_cache.db", check_same_thread=False)
        self.Cur = self.Conn.cursor()

        self.Cur.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            x INTEGER,
            z INTEGER,
            data TEXT,
            PRIMARY KEY(x,z)
        )
        """)

        self.Conn.commit()

    def Get(self, x, z):

        self.Cur.execute(
            "SELECT data FROM chunks WHERE x=? AND z=?",
            (x, z)
        )

        row = self.Cur.fetchone()

        if not row:
            return None

        return json.loads(row[0])

    def Save(self, x, z, Data):

        self.Cur.execute(
            "INSERT OR REPLACE INTO chunks VALUES (?, ?, ?)",
            (x, z, json.dumps(Data))
        )

        self.Conn.commit()
