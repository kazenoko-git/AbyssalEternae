# aurora_engine/ai/quest_cache.py

from aurora_engine.database.db_manager import DatabaseManager
import hashlib
import json
import time
from typing import Optional, Dict, List, Any
from aurora_engine.core.logging import get_logger

logger = get_logger()

class QuestCache:
    """
    Caches AI-generated quests to avoid redundant API calls.
    Also handles persistence of active quests.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def _compute_prompt_hash(self, prompt: str, context: dict) -> str:
        """Generate hash for prompt + context."""
        combined = prompt + json.dumps(context, sort_keys=True)
        return hashlib.sha256(combined.encode()).hexdigest()

    def get_cached_quest(self, prompt: str, context: dict) -> Optional[Dict]:
        """Retrieve cached quest data."""
        prompt_hash = self._compute_prompt_hash(prompt, context)

        result = self.db.fetch_one("""
            SELECT generated_content, metadata_json FROM ai_cache
            WHERE content_type = 'quest' AND prompt_hash = ?
        """, (prompt_hash,))

        if result:
            try:
                content = json.loads(result['generated_content'])
                metadata = json.loads(result['metadata_json']) if result.get('metadata_json') else {}
                return {'content': content, 'metadata': metadata}
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode cached quest content: {e}")
                return None
        return None

    def cache_quest(self, prompt: str, context: dict, quest_data: dict, metadata: dict = None):
        """Store generated quest in cache."""
        try:
            prompt_hash = self._compute_prompt_hash(prompt, context)
            quest_json = json.dumps(quest_data)
            metadata_json = json.dumps(metadata) if metadata else None

            self.db.execute("""
                INSERT OR REPLACE INTO ai_cache (content_type, prompt_hash, generated_content, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, ('quest', prompt_hash, quest_json, metadata_json, int(time.time())))

            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to cache quest: {e}")

    def save_quest_to_db(self, quest_id: str, title: str, description: str, objectives: Any, rewards: Dict, status: str = "active", npc_id_giver: str = None):
        """Save a quest definition to the quests table for persistence."""
        try:
            objectives_json = json.dumps(objectives)
            rewards_json = json.dumps(rewards)

            self.db.execute("""
                INSERT OR REPLACE INTO quests (quest_id, npc_id_giver, title, description, objectives_json, rewards_json, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (quest_id, npc_id_giver, title, description, objectives_json, rewards_json, status, int(time.time())))
            self.db.commit()
            logger.info(f"Saved quest '{title}' ({quest_id}) to database")
        except Exception as e:
            logger.error(f"Failed to save quest {quest_id}: {e}")

    def get_quest_from_db(self, quest_id: str) -> Optional[Dict]:
        """Retrieve a specific quest from the database."""
        result = self.db.fetch_one("""
            SELECT * FROM quests WHERE quest_id = ?
        """, (quest_id,))

        if result:
            return self._parse_quest_row(result)
        return None

    def get_active_quests(self) -> List[Dict]:
        """Retrieve all active quests."""
        results = self.db.fetch_all("""
            SELECT * FROM quests WHERE status = 'active'
        """)
        
        quests = []
        for row in results:
            quest = self._parse_quest_row(row)
            if quest:
                quests.append(quest)
        return quests

    def update_quest_status(self, quest_id: str, status: str):
        """Update the status of a quest."""
        try:
            self.db.execute("""
                UPDATE quests SET status = ? WHERE quest_id = ?
            """, (status, quest_id))
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to update quest status for {quest_id}: {e}")

    def _parse_quest_row(self, row: Dict) -> Optional[Dict]:
        """Helper to parse quest row from DB."""
        try:
            if 'objectives_json' in row:
                row['objectives'] = json.loads(row['objectives_json'])
            elif 'objectives' in row:
                row['objectives'] = json.loads(row['objectives'])

            if 'rewards_json' in row:
                row['rewards'] = json.loads(row['rewards_json'])
            elif 'rewards' in row:
                row['rewards'] = json.loads(row['rewards'])

            return row
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode quest data for {row.get('quest_id')}: {e}")
            return None
