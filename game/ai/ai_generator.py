# game_project/ai/ai_generator.py

import anthropic
import json
import time
from typing import Dict, List
from aurora_engine.database.db_manager import DatabaseManager
from aurora_engine.ai.dialogue_cache import DialogueCache
from aurora_engine.ai.npc_memory import NPCMemorySystem
from aurora_engine.core.logging import get_logger


class AIContentGenerator:
    """
    Game-layer AI content generator.
    Uses Anthropic API with caching.
    This is GAME code, not ENGINE code.
    """

    def __init__(self, db_manager: DatabaseManager):
        # Placeholder API key - in production use env var or config
        self.client = anthropic.Anthropic(api_key="YOUR_API_KEY_HERE")
        self.db = db_manager
        self.dialogue_cache = DialogueCache(db_manager)
        self.memory_system = NPCMemorySystem(db_manager)
        self.logger = get_logger()
        self.logger.info("AIContentGenerator initialized")

    def generate_npc_dialogue(self, npc_id: str, player_input: str, context: Dict) -> str:
        """
        Generate NPC dialogue response.
        Checks cache first, then calls API.
        """
        self.logger.info(f"Generating dialogue for NPC {npc_id}")
        
        # Check cache
        cached = self.dialogue_cache.get_cached_response(player_input, context)
        if cached:
            self.logger.debug("Dialogue cache hit")
            return cached

        # Get NPC memory for context
        memories = self.memory_system.get_recent_memories(npc_id, limit=5)

        # Build prompt
        prompt = self._build_dialogue_prompt(npc_id, player_input, memories, context)

        # Call API
        try:
            self.logger.debug("Calling Anthropic API")
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229", # Updated model name
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            dialogue = response.content[0].text
        except Exception as e:
            self.logger.error(f"AI Generation failed: {e}", exc_info=True)
            dialogue = "..."

        # Cache result
        self.dialogue_cache.cache_response(player_input, context, dialogue)

        # Store in dialogue history
        try:
            self.db.execute("""
                INSERT INTO dialogue_history (npc_id, player_line, npc_line, context_json, timestamp)
                VALUES (%s, %s, %s, %s, %s)
            """, (npc_id, player_input, dialogue, json.dumps(context), int(time.time())))
            self.db.commit()
        except Exception as e:
            self.logger.error(f"Failed to save dialogue history: {e}")

        return dialogue

    def _build_dialogue_prompt(self, npc_id: str, player_input: str,
                               memories: List[Dict], context: Dict) -> str:
        """Build prompt for dialogue generation."""
        # Get NPC profile
        npc_data = self.db.fetch_one("SELECT * FROM npcs WHERE npc_id = %s", (npc_id,))
        
        if not npc_data:
            # Fallback if NPC not in DB
            npc_data = {'name': 'Unknown', 'personality': 'Neutral', 'background': 'Unknown'}

        prompt = f"""You are {npc_data['name']}, an NPC in a fantasy RPG.

Personality: {npc_data['personality_json']}
Background: {npc_data['role']}

Recent memories:
"""
        for memory in memories:
            prompt += f"- {memory['description']}\n"

        prompt += f"""
Current context: {json.dumps(context)}

Player says: "{player_input}"

Respond as this character would, staying in character. Keep response under 100 words.
"""

        return prompt

    def generate_quest(self, quest_type: str, difficulty: int) -> Dict:
        """
        Generate a quest.
        Returns quest data structure.
        """
        self.logger.info(f"Generating {quest_type} quest (difficulty {difficulty})")
        
        # Check cache
        cache_key = f"{quest_type}_{difficulty}"
        cached = self.db.fetch_one("""
            SELECT generated_content FROM ai_cache
            WHERE content_type = 'quest' AND prompt_hash = %s
        """, (cache_key,))

        if cached:
            self.logger.debug("Quest cache hit")
            return json.loads(cached['generated_content'])

        # Generate new quest
        prompt = f"""Generate a {quest_type} quest for difficulty level {difficulty}.
Return JSON with: title, description, objectives (list), rewards (list).
Keep it concise and fitting a fantasy RPG setting."""

        try:
            self.logger.debug("Calling Anthropic API for quest")
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            quest_data = json.loads(response.content[0].text)
        except Exception as e:
            self.logger.error(f"Quest Generation failed: {e}", exc_info=True)
            quest_data = {
                "title": "Generic Quest",
                "description": "Something went wrong generating this quest.",
                "objectives": ["Report bug"],
                "rewards": []
            }

        # Cache
        try:
            self.db.execute("""
                INSERT INTO ai_cache (content_type, prompt_hash, generated_content, created_at)
                VALUES (%s, %s, %s, %s)
            """, ('quest', cache_key, json.dumps(quest_data), int(time.time())))
            self.db.commit()
        except Exception as e:
            self.logger.error(f"Failed to cache quest: {e}")

        return quest_data
