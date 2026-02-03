# game_project/systems/dialogue_system.py

from aurora_engine.ecs.system import System
from aurora_engine.ui.dialogue_box import DialogueBox
from game.components.npc import NPCController
from game.managers.ai_manager import AIManager
from aurora_engine.core.logging import get_logger
import json

logger = get_logger()

class DialogueSystem(System):
    """
    Handles NPC dialogue interactions.
    Game-specific system using AI manager.
    """

    def __init__(self, ui_manager):
        super().__init__()
        self.ui_manager = ui_manager
        self.dialogue_box = DialogueBox()
        self.active_npc = None

        # AI Manager (game layer)
        self.ai_manager: AIManager = None  # Set by game
        # logger.debug("DialogueSystem initialized")

    def get_required_components(self):
        return [NPCController]

    def update(self, entities, dt):
        """Process dialogue state."""
        # Update dialogue box animation
        if self.dialogue_box.visible:
            self.dialogue_box.update(dt)

    def start_dialogue(self, npc_entity, player_entity):
        """Begin dialogue with an NPC."""
        npc_controller = npc_entity.get_component(NPCController)
        self.active_npc = npc_entity
        logger.info(f"Starting dialogue with NPC {npc_controller.npc_id}")

        # Generate greeting
        context = {
            'location': 'village',
            'time_of_day': 'morning',
            'relationship': 'stranger'
        }

        # Use AI Manager if available, otherwise fallback (or fail gracefully)
        if self.ai_manager:
            greeting = self.ai_manager.generate_dialogue(
                npc_controller.npc_id,
                "[GREETING]",
                context
            )
        else:
            greeting = "Hello there."

        # Show dialogue box
        self.dialogue_box.show_dialogue(npc_controller.npc_name, greeting)
        self.ui_manager.add_widget(self.dialogue_box, 'overlay')

        # Add dialogue choices
        self._add_dialogue_choices(npc_controller)

    def _add_dialogue_choices(self, npc_controller):
        """Add player dialogue options."""
        choices = [
            ("Ask about the village", lambda: self._player_choice(0)),
            ("Ask for a quest", lambda: self._request_quest(npc_controller)),
            ("Goodbye", lambda: self._end_dialogue())
        ]

        for choice_text, callback in choices:
            self.dialogue_box.add_choice(choice_text, callback)

    def _request_quest(self, npc_controller):
        """Handle player requesting a quest."""
        logger.info(f"Player requested quest from {npc_controller.npc_id}")
        
        if self.ai_manager:
            # Generate quest
            quest_data = self.ai_manager.generate_quest(
                npc_controller.npc_id,
                context={'difficulty': 1}
            )
            
            if quest_data:
                # Format response
                response = f"I have a task for you: {quest_data['title']}.\n{quest_data['description']}"
                
                # Update dialogue box
                self.dialogue_box.clear_choices()
                self.dialogue_box.show_dialogue(npc_controller.npc_name, response)
                
                # Add accept/decline choices
                self.dialogue_box.add_choice("Accept Quest", lambda: self._accept_quest(quest_data))
                self.dialogue_box.add_choice("Decline", lambda: self._add_dialogue_choices(npc_controller))
                return

        # Fallback if no quest generated
        self.dialogue_box.show_dialogue(npc_controller.npc_name, "I have nothing for you right now.")
        self._add_dialogue_choices(npc_controller)

    def _accept_quest(self, quest_data):
        """Handle quest acceptance."""
        logger.info(f"Player accepted quest: {quest_data['title']}")
        # Here we would add the quest to the player's quest log
        # For now just close dialogue or go back to main menu
        self._end_dialogue()

    def _player_choice(self, choice_index: int):
        """Handle player dialogue choice."""
        npc_controller = self.active_npc.get_component(NPCController)

        # Map choice to player input
        player_inputs = [
            "Tell me about this village.",
            "Do you have any work for me?",
        ]
        
        if choice_index < len(player_inputs):
            player_input = player_inputs[choice_index]
        else:
            player_input = "..."

        if self.ai_manager:
            # Generate NPC response
            context = {'dialogue_stage': choice_index}
            response = self.ai_manager.generate_dialogue(
                npc_controller.npc_id,
                player_input,
                context
            )
        else:
            response = "..."

        # Update dialogue box
        self.dialogue_box.clear_choices()
        self.dialogue_box.show_dialogue(npc_controller.npc_name, response)

        # Add new choices
        self._add_dialogue_choices(npc_controller)

    def _end_dialogue(self):
        """End current dialogue."""
        self.dialogue_box.visible = False
        self.ui_manager.remove_widget(self.dialogue_box)
        if self.active_npc:
            npc_controller = self.active_npc.get_component(NPCController)
            logger.info(f"Ending dialogue with NPC {npc_controller.npc_id}")
        self.active_npc = None
