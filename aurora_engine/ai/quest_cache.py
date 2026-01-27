# aurora_engine/ai/quest_cache.py

from aurora_engine.database.db_manager import DatabaseManager
import hashlib
import json
import time
from typing import Optional, Dict, List


class QuestCache:
    """
    Caches AI-generated quests to avoid redundant API calls.
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
            SELECT generated_content, metadata FROM ai_cache
            WHERE content_type = 'quest' AND prompt_hash = ?
        """, (prompt_hash,))

        if result:
            content = json.loads(result['generated_content'])
            metadata = json.loads(result['metadata']) if result['metadata'] else {}
            return {'content': content, 'metadata': metadata}
        return None

    def cache_quest(self, prompt: str, context: dict, quest_data: dict, metadata: dict = None):
        """Store generated quest in cache."""
        prompt_hash = self._compute_prompt_hash(prompt, context)
        quest_json = json.dumps(quest_data)
        metadata_json = json.dumps(metadata) if metadata else None

        self.db.execute("""
            INSERT OR REPLACE INTO ai_cache (content_type, prompt_hash, generated_content, metadata, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, ('quest', prompt_hash, quest_json, metadata_json, int(time.time())))

        self.db.commit()

    def save_quest_to_db(self, quest_id: str, title: str, description: str, objectives: List[str], rewards: Dict, status: str = "active"):
        """Save a quest definition to the quests table for persistence."""
        objectives_json = json.dumps(objectives)
        rewards_json = json.dumps(rewards)

        self.db.execute("""
            INSERT OR REPLACE INTO quests (quest_id, title, description, objectives, rewards, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (quest_id, title, description, objectives_json, rewards_json, status, int(time.time())))
        self.db.commit()

    def get_quest_from_db(self, quest_id: str) -> Optional[Dict]:
        """Retrieve a specific quest from the database."""
        result = self.db.fetch_one("""
            SELECT * FROM quests WHERE quest_id = ?
        """, (quest_id,))

        if result:
            result['objectives'] = json.loads(result['objectives'])
            result['rewards'] = json.loads(result['rewards'])
            return result
        return None

    def get_active_quests(self) -> List[Dict]:
        """Retrieve all active quests."""
        results = self.db.fetch_all("""
            SELECT * FROM quests WHERE status = 'active'
        """)
        
        quests = []
        for row in results:
            row['objectives'] = json.loads(row['objectives'])
            row['rewards'] = json.loads(row['rewards'])
            quests.append(row)
        return quests

    def update_quest_status(self, quest_id: str, status: str):
        """Update the status of a quest."""
        self.db.execute("""
            UPDATE quests SET status = ? WHERE quest_id = ?
        """, (status, quest_id))
        self.db.commit()
