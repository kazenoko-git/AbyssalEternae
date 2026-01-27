# aurora_engine/ai/dialogue_cache.py

from aurora_engine.database.db_manager import DatabaseManager
import hashlib
import json
import time


class DialogueCache:
    """
    Caches AI-generated dialogue to avoid redundant API calls.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def _compute_prompt_hash(self, prompt: str, context: dict) -> str:
        """Generate hash for prompt + context."""
        combined = prompt + json.dumps(context, sort_keys=True)
        return hashlib.sha256(combined.encode()).hexdigest()

    def get_cached_response(self, prompt: str, context: dict) -> str:
        """Retrieve cached dialogue response."""
        prompt_hash = self._compute_prompt_hash(prompt, context)

        result = self.db.fetch_one("""
            SELECT generated_content FROM ai_cache
            WHERE content_type = 'dialogue' AND prompt_hash = ?
        """, (prompt_hash,))

        return result['generated_content'] if result else None

    def cache_response(self, prompt: str, context: dict, response: str, metadata: dict = None):
        """Store generated dialogue in cache."""
        prompt_hash = self._compute_prompt_hash(prompt, context)
        metadata_json = json.dumps(metadata) if metadata else None

        self.db.execute("""
            INSERT OR REPLACE INTO ai_cache (content_type, prompt_hash, generated_content, metadata, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, ('dialogue', prompt_hash, response, metadata_json, int(time.time())))

        self.db.commit()