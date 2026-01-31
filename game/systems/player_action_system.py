# game_project/systems/player_action_system.py

from aurora_engine.ecs.system import System
from game.components.player import PlayerController
from aurora_engine.input.input_manager import InputManager
from aurora_engine.core.logging import get_logger

class PlayerActionSystem(System):
    """
    Handles player actions like Attacking, Blocking, Interaction, and UI Toggles.
    """
    
    def __init__(self, input_manager: InputManager, ui_manager=None):
        super().__init__()
        self.input_manager = input_manager
        self.ui_manager = ui_manager
        self.logger = get_logger()

    def get_required_components(self):
        return [PlayerController]

    def update(self, entities, dt):
        for entity in entities:
            controller = entity.get_component(PlayerController)
            
            # Cooldown management
            if controller.attack_cooldown > 0:
                controller.attack_cooldown -= dt
            
            # Attack (Left Click)
            if self.input_manager.is_key_down("mouse1"):
                if controller.attack_cooldown <= 0 and not controller.is_blocking:
                    self._perform_attack(controller)
            else:
                controller.is_attacking = False
                
            # Block (E)
            if self.input_manager.is_key_down("e"):
                controller.is_blocking = True
            else:
                controller.is_blocking = False
                
            # Ultimate (Q)
            if self.input_manager.is_key_down("q"):
                self._perform_ultimate(controller)
                
            # Interact (G)
            if self.input_manager.is_key_down("g"):
                self._interact(entity)
                
            # Quick Slots (1, 2, 3)
            if self.input_manager.is_key_down("1"):
                self.logger.info("Selected Quick Slot 1")
            if self.input_manager.is_key_down("2"):
                self.logger.info("Selected Quick Slot 2")
            if self.input_manager.is_key_down("3"):
                self.logger.info("Selected Quick Slot 3")
                
            # UI Toggles (Just logging for now, would toggle UI widgets)
            if self.input_manager.is_key_down("f"):
                self.logger.info("Toggle Inventory")
            if self.input_manager.is_key_down("m"):
                self.logger.info("Toggle Map")
            if self.input_manager.is_key_down("j"):
                self.logger.info("Toggle Quest Menu")

    def _perform_attack(self, controller):
        controller.is_attacking = True
        controller.attack_cooldown = 0.5 # Simple cooldown
        self.logger.info("Player Attacking!")
        # Here we would trigger animation or deal damage

    def _perform_ultimate(self, controller):
        self.logger.info("Player Unleashed Ultimate!")
        # Trigger VFX

    def _interact(self, player_entity):
        # Raycast forward to find interactable
        # For now just log
        self.logger.info("Player interacting...")
