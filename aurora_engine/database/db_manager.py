# aurora_engine/database/db_manager.py

import sqlite3
from typing import Optional, List, Dict, Any
from pathlib import Path


class DatabaseManager:
    """
    SQLite database manager.
    Handles connections, queries, and transactions.
    """

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.connection: Optional[sqlite3.Connection] = None

    def connect(self):
        """Open database connection."""
        # check_same_thread=False allows sharing connection across threads
        # This is necessary for async world generation
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row  # Dict-like access

    def disconnect(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query."""
        if not self.connection:
            raise RuntimeError("Database not connected")

        cursor = self.connection.cursor()
        cursor.execute(query, params)
        return cursor

    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Execute query and return one result."""
        cursor = self.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute query and return all results."""
        cursor = self.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def commit(self):
        """Commit transaction."""
        if self.connection:
            self.connection.commit()

    def rollback(self):
        """Rollback transaction."""
        if self.connection:
            self.connection.rollback()
