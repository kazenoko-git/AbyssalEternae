# aurora_engine/ai/npc_memory.py

from typing import List, Dict
from aurora_engine.database.db_manager import DatabaseManager
import time
from aurora_engine.core.logging import get_logger

logger = get_logger()

class NPCMemorySystem:
    """
    NPC memory system.
    Stores and retrieves NPC memories for AI context.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def add_memory(self, npc_id: str, event_type: str, description: str, emotional_impact: float = 0.0):
        """Store a new memory for an NPC."""
        try:
            self.db.execute("""
                INSERT INTO npc_memory (npc_id, event_type, description, emotional_impact, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (npc_id, event_type, description, emotional_impact, int(time.time())))
            self.db.commit()
            # logger.debug(f"Added memory for NPC {npc_id}: {event_type}")
        except Exception as e:
            logger.error(f"Failed to add memory for NPC {npc_id}: {e}")

    def get_recent_memories(self, npc_id: str, limit: int = 10) -> List[Dict]:
        """Retrieve recent memories for an NPC."""
        return self.db.fetch_all("""
            SELECT * FROM npc_memory
            WHERE npc_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (npc_id, limit))

    def get_memories_by_type(self, npc_id: str, event_type: str) -> List[Dict]:
        """Retrieve memories of a specific type."""
        return self.db.fetch_all("""
            SELECT * FROM npc_memory
            WHERE npc_id = ? AND event_type = ?
            ORDER BY timestamp DESC
        """, (npc_id, event_type))

    def get_emotionally_significant_memories(self, npc_id: str, threshold: float = 0.5) -> List[Dict]:
        """Retrieve memories above an emotional threshold."""
        return self.db.fetch_all("""
            SELECT * FROM npc_memory
            WHERE npc_id = ? AND ABS(emotional_impact) >= ?
            ORDER BY timestamp DESC
        """, (npc_id, threshold))
