# game_project/ai/ai_generator.py

import json
import time
import os
from typing import Dict, List
from aurora_engine.database.db_manager import DatabaseManager
from aurora_engine.core.logging import get_logger
from game.ai.quest_slm import QuestSLM


class AIContentGenerator:
    """
    Game-layer AI content generator.
    Supports multiple free providers (Groq, Gemini, Hugging Face).
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
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
                self.api_key = os.environ.get("HF_API_KEY")
                if self.api_key:
                    self.provider = "huggingface"
                else:
                    self.logger.warning("No AI API keys found (GROQ_API_KEY, GEMINI_API_KEY, HF_API_KEY). AI features will fail.")

        self.quest_slm = QuestSLM(self.api_key, provider=self.provider)
        self.logger.info(f"AIContentGenerator initialized using {self.provider.upper()}")

    def generate_dialogue(self, npc_id: str, player_input: str, context: Dict) -> str:
        """Generate NPC dialogue response."""
        # Note: Caching and memory retrieval are now handled by AIManager.
        # This method purely handles the generation logic.

        npc_data = self.db.fetch_one("SELECT * FROM npcs WHERE npc_id = %s", (npc_id,)) or {'name': 'Unknown', 'personality_json': '{}', 'role': 'Unknown'}
        
        memories = context.get('memories', [])
        emotion = context.get('emotion', {})

        prompt = f"""Roleplay as {npc_data['name']} ({npc_data['role']}).
Personality: {npc_data['personality_json']}
Current Emotion: {json.dumps(emotion)}
Relevant Memories: {[m['description'] for m in memories]}
Context: {json.dumps(context)}
Player: "{player_input}"
Response (under 50 words):"""

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

        return response_text

    def generate_quest(self, npc_id: str, context: Dict) -> Dict:
        """Generate a quest."""
        # Note: Caching is now handled by AIManager.
        
        npc_context = {}
        if npc_id:
            npc_data = self.db.fetch_one("SELECT * FROM npcs WHERE npc_id = %s", (npc_id,))
            if npc_data:
                npc_context = {"name": npc_data['name'], "role": npc_data['role'], "personality": npc_data['personality_json']}

        quest_data = self.quest_slm.generate_quest_flow(
            theme=context.get('theme', 'Adventure'),
            difficulty=context.get('difficulty', 1),
            npc_giver_context=npc_context,
            world_context={"biome": "Forest", "time": "Day"}
        )

        if not quest_data:
            quest_data = {"title": "Generic Quest", "description": "Generation failed.", "objectives": [], "rewards": {}}
            
        # Ensure ID is present
        if 'id' not in quest_data:
            quest_data['id'] = f"quest_{int(time.time())}"

        return quest_data
