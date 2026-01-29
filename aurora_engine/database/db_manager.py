# aurora_engine/database/db_manager.py

import mysql.connector
from typing import Optional, List, Dict, Any
import threading
from aurora_engine.core.logging import get_logger


class DatabaseManager:
    """
    MySQL database manager.
    Handles connections, queries, and transactions.
    Uses thread-local storage for connections to ensure thread safety without complex pooling.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.local = threading.local() # Thread-local storage
        self.logger = get_logger()
        self.logger.info("DatabaseManager initialized")

    def _get_connection(self):
        """Get or create a connection for the current thread."""
        if not hasattr(self.local, 'connection') or self.local.connection is None or not self.local.connection.is_connected():
            dbconfig = {
                "host": self.config.get("host", "localhost"),
                "user": self.config.get("user", "root"),
                "password": self.config.get("password", ""),
                "database": self.config.get("database", "rifted_db"),
                "port": self.config.get("port", 3306),
                "autocommit": False # We handle commit manually
            }
            try:
                self.local.connection = mysql.connector.connect(**dbconfig)
                self.logger.info(f"Connected to MySQL database: {dbconfig['database']}")
            except mysql.connector.Error as err:
                self.logger.critical(f"Error connecting to MySQL: {err}")
                raise
        return self.local.connection

    def connect(self):
        """Initialize connection (for main thread)."""
        self._get_connection()

    def disconnect(self):
        """Close database connection for current thread."""
        if hasattr(self.local, 'connection') and self.local.connection:
            self.local.connection.close()
            self.local.connection = None
            self.logger.info("Disconnected from MySQL")

    def execute(self, query: str, params: tuple = ()) -> Any:
        """Execute a query."""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        try:
            cursor.execute(query, params)
            return cursor
        except mysql.connector.Error as err:
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
