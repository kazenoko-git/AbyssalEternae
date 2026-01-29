# aurora_engine/database/queries.py

from typing import List, Dict, Optional, Any
from aurora_engine.database.db_manager import DatabaseManager
from aurora_engine.core.logging import get_logger

logger = get_logger()

class PreparedQueries:
    """
    Collection of prepared/optimized queries.
    Reduces SQL duplication and improves performance.
    """

    def __init__(self, db: DatabaseManager):
        self.db = db

    # NPC Queries
    def get_npc(self, npc_id: str) -> Optional[Dict]:
        """Get NPC by ID."""
        return self.db.fetch_one(
            "SELECT * FROM npcs WHERE npc_id = ?",
            (npc_id,)
        )

    def create_npc(self, npc_id: str, name: str, personality: str, background: str) -> bool:
        """Create new NPC."""
        try:
            import time
            self.db.execute(
                """INSERT INTO npcs (npc_id, name, personality, background, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (npc_id, name, personality, background, int(time.time()))
            )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to create NPC {npc_id}: {e}")
            self.db.rollback()
            return False

    def update_npc(self, npc_id: str, **kwargs) -> bool:
        """Update NPC fields."""
        if not kwargs:
            return False

        # Build SET clause
        set_parts = [f"{key} = ?" for key in kwargs.keys()]
        values = list(kwargs.values())
        values.append(npc_id)

        try:
            self.db.execute(
                f"UPDATE npcs SET {', '.join(set_parts)} WHERE npc_id = ?",
                tuple(values)
            )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update NPC {npc_id}: {e}")
            self.db.rollback()
            return False

    # Memory Queries
    def add_npc_memory(self, npc_id: str, event_type: str, description: str,
                       emotional_impact: float = 0.0):
        """Add memory for NPC."""
        import time
        try:
            self.db.execute(
                """INSERT INTO npc_memory (npc_id, event_type, description, emotional_impact, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (npc_id, event_type, description, emotional_impact, int(time.time()))
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to add memory for NPC {npc_id}: {e}")
            self.db.rollback()

    def get_npc_memories(self, npc_id: str, limit: int = 10) -> List[Dict]:
        """Get recent NPC memories."""
        return self.db.fetch_all(
            """SELECT * FROM npc_memory 
               WHERE npc_id = ? 
               ORDER BY timestamp DESC 
               LIMIT ?""",
            (npc_id, limit)
        )

    def get_memories_by_emotion(self, npc_id: str, min_impact: float) -> List[Dict]:
        """Get emotionally significant memories."""
        return self.db.fetch_all(
            """SELECT * FROM npc_memory 
               WHERE npc_id = ? AND ABS(emotional_impact) >= ?
               ORDER BY timestamp DESC""",
            (npc_id, min_impact)
        )

    # Quest Queries
    def create_quest(self, quest_id: str, title: str, description: str,
                     objectives: str, rewards: str, status: str = 'available'):
        """Create new quest."""
        import time
        try:
            self.db.execute(
                """INSERT INTO quests (quest_id, title, description, objectives, rewards, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (quest_id, title, description, objectives, rewards, status, int(time.time()))
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to create quest {quest_id}: {e}")
            self.db.rollback()

    def get_quest(self, quest_id: str) -> Optional[Dict]:
        """Get quest by ID."""
        return self.db.fetch_one(
            "SELECT * FROM quests WHERE quest_id = ?",
            (quest_id,)
        )

    def get_quests_by_status(self, status: str) -> List[Dict]:
        """Get all quests with status."""
        return self.db.fetch_all(
            "SELECT * FROM quests WHERE status = ?",
            (status,)
        )

    def update_quest_status(self, quest_id: str, status: str):
        """Update quest status."""
        try:
            self.db.execute(
                "UPDATE quests SET status = ? WHERE quest_id = ?",
                (status, quest_id)
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to update quest status for {quest_id}: {e}")
            self.db.rollback()

    # AI Cache Queries
    def get_cached_content(self, content_type: str, prompt_hash: str) -> Optional[str]:
        """Get cached AI-generated content."""
        result = self.db.fetch_one(
            """SELECT generated_content FROM ai_cache 
               WHERE content_type = ? AND prompt_hash = ?""",
            (content_type, prompt_hash)
        )
        return result['generated_content'] if result else None

    def cache_content(self, content_type: str, prompt_hash: str, content: str, metadata: str = None):
        """Cache AI-generated content."""
        import time
        try:
            self.db.execute(
                """INSERT OR REPLACE INTO ai_cache 
                   (content_type, prompt_hash, generated_content, metadata, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (content_type, prompt_hash, content, metadata, int(time.time()))
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to cache content: {e}")
            self.db.rollback()
