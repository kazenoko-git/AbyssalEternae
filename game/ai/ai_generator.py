# game_project/ai/ai_generator.py

import json
import time
import os
from typing import Dict, List
from aurora_engine.database.db_manager import DatabaseManager
from aurora_engine.ai.dialogue_cache import DialogueCache
from aurora_engine.ai.npc_memory import NPCMemorySystem
from aurora_engine.core.logging import get_logger
from game.ai.quest_slm import QuestSLM


class AIContentGenerator:
    """
    Game-layer AI content generator.
    Supports multiple free providers (Groq, Gemini, Hugging Face).
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.dialogue_cache = DialogueCache(db_manager)
        self.memory_system = NPCMemorySystem(db_manager)
        self.logger = get_logger()
        
        # Determine provider and key from environment
        self.provider = "groq" # Default to Groq as it's fast and free
        self.api_key = os.environ.get("GROQ_API_KEY")

        if not self.api_key:
            # Fallback to Gemini
            self.api_key = os.environ.get("GEMINI_API_KEY")
            if self.api_key:
                self.provider = "gemini"
            else:
                # Fallback to Hugging Face
                self.api_key = ""
                if self.api_key:
                    self.provider = "huggingface"
                else:
                    self.logger.warning("No AI API keys found (GROQ_API_KEY, GEMINI_API_KEY, HF_API_KEY). AI features will fail.")

        self.quest_slm = QuestSLM(self.api_key, provider=self.provider)
        self.logger.info(f"AIContentGenerator initialized using {self.provider.upper()}")

    def generate_npc_dialogue(self, npc_id: str, player_input: str, context: Dict) -> str:
        """Generate NPC dialogue response."""
        # Check cache
        cached = self.dialogue_cache.get_cached_response(player_input, context)
        if cached:
            return cached

        # Get context
        memories = self.memory_system.get_recent_memories(npc_id, limit=5)
        npc_data = self.db.fetch_one("SELECT * FROM npcs WHERE npc_id = %s", (npc_id,)) or {'name': 'Unknown', 'personality_json': '{}', 'role': 'Unknown'}

        prompt = f"""Roleplay as {npc_data['name']} ({npc_data['role']}).
Personality: {npc_data['personality_json']}
Memories: {[m['description'] for m in memories]}
Context: {json.dumps(context)}
Player: "{player_input}"
Response (under 50 words):"""

        # Use the same provider logic as QuestSLM, but simplified for text
        # For now, we can reuse the internal generation methods of QuestSLM if we exposed them, 
        # or just instantiate a temporary helper. 
        # To keep it clean, let's just use the QuestSLM instance's internal methods since they are generic enough
        # or add a generic generate_text method to QuestSLM.
        
        # For this implementation, I'll add a quick hack to use the specific provider method directly
        # Ideally, QuestSLM should be renamed to LLMClient or similar.
        
        response_text = "..."
        try:
            if self.provider == "groq":
                response_text = self.quest_slm._generate_groq(prompt)
            elif self.provider == "gemini":
                response_text = self.quest_slm._generate_gemini(prompt)
            elif self.provider == "huggingface":
                response_text = self.quest_slm._generate_huggingface(prompt)
                
            # Clean up JSON artifacts if the model was confused by previous system prompts
            if response_text:
                if "{" in response_text and "}" in response_text:
                     # It might have output JSON, try to extract text if it's a JSON object with "response" key
                     try:
                         data = json.loads(response_text)
                         if "response" in data:
                             response_text = data["response"]
                     except:
                         pass
        except Exception as e:
            self.logger.error(f"Dialogue generation failed: {e}")

        if not response_text:
            response_text = "..."

        # Cache and Store
        self.dialogue_cache.cache_response(player_input, context, response_text)
        try:
            self.db.execute("INSERT INTO dialogue_history (npc_id, player_line, npc_line, context_json, timestamp) VALUES (%s, %s, %s, %s, %s)", 
                           (npc_id, player_input, response_text, json.dumps(context), int(time.time())))
            self.db.commit()
        except Exception:
            pass

        return response_text

    def generate_quest(self, quest_type: str, difficulty: int, npc_id: str = None) -> Dict:
        """Generate a quest."""
        cache_key = f"{quest_type}_{difficulty}_{npc_id}"
        cached = self.db.fetch_one("SELECT generated_content FROM ai_cache WHERE content_type = 'quest' AND prompt_hash = %s", (cache_key,))
        if cached:
            return json.loads(cached['generated_content'])

        npc_context = {}
        if npc_id:
            npc_data = self.db.fetch_one("SELECT * FROM npcs WHERE npc_id = %s", (npc_id,))
            if npc_data:
                npc_context = {"name": npc_data['name'], "role": npc_data['role'], "personality": npc_data['personality_json']}

        quest_data = self.quest_slm.generate_quest_flow(
            theme=quest_type,
            difficulty=difficulty,
            npc_giver_context=npc_context,
            world_context={"biome": "Forest", "time": "Day"}
        )

        if not quest_data:
            quest_data = {"title": "Generic Quest", "description": "Generation failed.", "objectives": [], "rewards": {}}

        try:
            self.db.execute("INSERT INTO ai_cache (content_type, prompt_hash, generated_content, created_at) VALUES (%s, %s, %s, %s)", 
                           ('quest', cache_key, json.dumps(quest_data), int(time.time())))
            self.db.commit()
        except Exception:
            pass

        return quest_data
