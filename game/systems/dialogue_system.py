# game_project/systems/dialogue_system.py

from aurora_engine.ecs.system import System
from aurora_engine.ui.dialogue_box import DialogueBox
from game.components.npc import NPCController
from game.ai.ai_generator import AIContentGenerator
from aurora_engine.core.logging import get_logger

logger = get_logger()

class DialogueSystem(System):
    """
    Handles NPC dialogue interactions.
    Game-specific system using AI generator.
    """

    def __init__(self, ui_manager):
        super().__init__()
        self.ui_manager = ui_manager
        self.dialogue_box = DialogueBox()
        self.active_npc = None

        # AI generator (game layer)
        from aurora_engine.core.application import Application
        # Access via game instance
        self.ai_generator = None  # Set by game
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

        greeting = self.ai_generator.generate_npc_dialogue(
            npc_controller.npc_id,
            "[GREETING]",
            context
        )

        # Show dialogue box
        self.dialogue_box.show_dialogue(npc_controller.npc_name, greeting)
        self.ui_manager.add_widget(self.dialogue_box, 'overlay')

        # Add dialogue choices
        self._add_dialogue_choices(npc_controller)

    def _add_dialogue_choices(self, npc_controller):
        """Add player dialogue options."""
        choices = [
            ("Ask about the village", lambda: self._player_choice(0)),
            ("Ask for a quest", lambda: self._player_choice(1)),
            ("Goodbye", lambda: self._end_dialogue())
        ]

        for choice_text, callback in choices:
            self.dialogue_box.add_choice(choice_text, callback)

    def _player_choice(self, choice_index: int):
        """Handle player dialogue choice."""
        npc_controller = self.active_npc.get_component(NPCController)

        # Map choice to player input
        player_inputs = [
            "Tell me about this village.",
            "Do you have any work for me?",
        ]

        # Generate NPC response
        context = {'dialogue_stage': choice_index}
        response = self.ai_generator.generate_npc_dialogue(
            npc_controller.npc_id,
            player_inputs[choice_index],
            context
        )

        # Update dialogue box
        self.dialogue_box.clear_choices()
        self.dialogue_box.show_dialogue(npc_controller.npc_name, response)

        # Add new choices
        self._add_dialogue_choices(npc_controller)

        # Store memory
        self.ai_generator.memory_system.add_memory(
            npc_controller.npc_id,
            'dialogue',
            f"Player asked: {player_inputs[choice_index]}",
            emotional_impact=0.1
        )

    def _end_dialogue(self):
        """End current dialogue."""
        self.dialogue_box.visible = False
        self.ui_manager.remove_widget(self.dialogue_box)
        if self.active_npc:
            npc_controller = self.active_npc.get_component(NPCController)
            logger.info(f"Ending dialogue with NPC {npc_controller.npc_id}")
        self.active_npc = None
