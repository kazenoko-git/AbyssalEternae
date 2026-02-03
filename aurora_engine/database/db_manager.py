# aurora_engine/database/db_manager.py

import sqlite3
from typing import Optional, List, Dict, Any
import threading
from aurora_engine.core.logging import get_logger


class DatabaseManager:
    """
    SQLite database manager.
    Handles connections, queries, and transactions.
    Uses thread-local storage for connections to ensure thread safety.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.local = threading.local() # Thread-local storage
        self.logger = get_logger()
        self.logger.info("DatabaseManager initialized (SQLite)")

    def _get_connection(self):
        """Get or create a connection for the current thread."""
        if not hasattr(self.local, 'connection') or self.local.connection is None:
            db_name = self.config.get("database", "eternae.db")
            if not db_name.endswith(".db"):
                db_name += ".db"
                
            try:
                self.local.connection = sqlite3.connect(db_name)
                self.local.connection.row_factory = self._dict_factory
                self.local.connection.execute("PRAGMA foreign_keys = ON")
                self.logger.info(f"Connected to SQLite database: {db_name}")
            except sqlite3.Error as err:
                self.logger.critical(f"Error connecting to SQLite: {err}")
                raise
        return self.local.connection

    def _dict_factory(self, cursor, row):
        """Convert row to dictionary."""
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    def connect(self):
        """Initialize connection (for main thread)."""
        self._get_connection()

    def disconnect(self):
        """Close database connection for current thread."""
        if hasattr(self.local, 'connection') and self.local.connection:
            self.local.connection.close()
            self.local.connection = None
            self.logger.info("Disconnected from SQLite")

    def execute(self, query: str, params: tuple = ()) -> Any:
        """Execute a query."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # Convert MySQL style placeholders (%s) to SQLite style (?)
            query = query.replace("%s", "?")
            
            cursor.execute(query, params)
            return cursor
        except sqlite3.Error as err:
            self.logger.error(f"Query failed: {err}")
            self.logger.debug(f"Query: {query}")
            self.logger.debug(f"Params: {params}")
            raise

    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Execute query and return one result."""
        cursor = self.execute(query, params)
        row = cursor.fetchone()
        cursor.close()
        return row

    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute query and return all results."""
        cursor = self.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def commit(self):
        """Commit transaction."""
        conn = self._get_connection()
        conn.commit()

    def rollback(self):
        """Rollback transaction."""
        conn = self._get_connection()
        conn.rollback()
