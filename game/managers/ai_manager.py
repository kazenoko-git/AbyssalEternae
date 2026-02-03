# game/managers/ai_manager.py

from typing import Dict, Optional, List
from aurora_engine.database.db_manager import DatabaseManager
from aurora_engine.ai.npc_memory import NPCMemorySystem
from aurora_engine.ai.emotion_state import EmotionState
from aurora_engine.ai.dialogue_cache import DialogueCache
from aurora_engine.ai.quest_cache import QuestCache
from game.ai.ai_generator import AIContentGenerator
from aurora_engine.core.logging import get_logger

logger = get_logger()

class AIManager:
    """
    Manages AI-related systems including NPC memory, emotions, dialogue, and quest generation.
    Acts as a facade for various AI subsystems.
    """
    
    def __init__(self, db_manager: DatabaseManager, ai_generator: AIContentGenerator):
        self.db_manager = db_manager
        self.ai_generator = ai_generator
        
        # Subsystems
        self.memory_system = NPCMemorySystem(db_manager)
        self.dialogue_cache = DialogueCache(db_manager)
        self.quest_cache = QuestCache(db_manager)
        
        # Runtime state
        self.npc_emotion_states: Dict[str, EmotionState] = {}

    def get_npc_emotion_state(self, npc_id: str) -> EmotionState:
        """Get or create emotion state for an NPC."""
        if npc_id not in self.npc_emotion_states:
            self.npc_emotion_states[npc_id] = EmotionState()
        return self.npc_emotion_states[npc_id]

    def update_emotions(self, dt: float):
        """Update emotion states for all active NPCs."""
        for state in self.npc_emotion_states.values():
            state.update(dt)

    def generate_dialogue(self, npc_id: str, player_input: str, context: Dict) -> str:
        """Generate dialogue response using AI, checking cache first."""
        # Add memory and emotion to context
        memories = self.memory_system.get_recent_memories(npc_id, limit=5)
        emotion_state = self.get_npc_emotion_state(npc_id)
        
        full_context = {
            **context,
            "memories": memories,
            "emotion": emotion_state.to_dict()
        }
        
        # Check cache
        cached = self.dialogue_cache.get_cached_response(player_input, full_context)
        if cached:
            return cached
            
        # Generate
        response = self.ai_generator.generate_dialogue(npc_id, player_input, full_context)
        
        # Cache
        self.dialogue_cache.cache_response(player_input, full_context, response)
        
        # Update memory
        self.memory_system.add_memory(npc_id, "dialogue", f"Player said: {player_input}. I replied: {response}")
        
        return response

    def generate_quest(self, npc_id: str, context: Dict) -> Dict:
        """Generate a quest from an NPC."""
        # Check cache/existing quests logic could go here
        
        quest = self.ai_generator.generate_quest(npc_id, context)
        
        if quest:
            self.quest_cache.save_quest_to_db(
                quest['id'], 
                quest['title'], 
                quest['description'], 
                quest['objectives'], 
                quest['rewards'], 
                npc_id_giver=npc_id
            )
            
        return quest
