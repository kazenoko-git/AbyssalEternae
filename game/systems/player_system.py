# game_project/systems/player_system.py

from aurora_engine.ecs.system import System
from aurora_engine.scene.transform import Transform
from game.components.player import PlayerController
from aurora_engine.input.input_manager import InputManager
from aurora_engine.input.action_map import InputDevice
import numpy as np


class PlayerSystem(System):
    """
    Player movement system.
    This is GAME logic built on ENGINE components.
    """
    
    def __init__(self, input_manager: InputManager):
        super().__init__()
        self.input_manager = input_manager
        self._setup_input()

    def _setup_input(self):
        """Setup input context for player."""
        self.context = self.input_manager.create_context("Player")
        
        # Move
        self.context.action_map.create_action("MoveForward").add_binding(InputDevice.KEYBOARD, "w")
        self.context.action_map.create_action("MoveBackward").add_binding(InputDevice.KEYBOARD, "s")
        self.context.action_map.create_action("MoveLeft").add_binding(InputDevice.KEYBOARD, "a")
        self.context.action_map.create_action("MoveRight").add_binding(InputDevice.KEYBOARD, "d")
        
        self.input_manager.set_active_context(self.context)

    def get_required_components(self):
        return [Transform, PlayerController]

    def update(self, entities, dt):
        """Update player movement."""
        
        # Poll input state
        # Note: InputManager.poll() is called by Application, but we need to check actions here.
        # Since InputManager stores state, we can query it via context.
        # But context.process_input is callback based.
        # For movement, we often want polling "is_down".
        # Let's use the action map directly or check state.
        
        # We need a way to query "is action active" from the system.
        # InputContext has `process_input` which triggers callbacks.
        # But for continuous movement, we want `is_action_active`.
        
        input_state = self.input_manager._input_state # Access raw state (hacky but works for now)
        
        move_dir = np.zeros(3, dtype=np.float32)
        
        if self.context.action_map.is_action_active("MoveForward", input_state):
            move_dir[1] += 1.0
        if self.context.action_map.is_action_active("MoveBackward", input_state):
            move_dir[1] -= 1.0
        if self.context.action_map.is_action_active("MoveLeft", input_state):
            move_dir[0] -= 1.0
        if self.context.action_map.is_action_active("MoveRight", input_state):
            move_dir[0] += 1.0
            
        if np.linalg.norm(move_dir) > 0:
            move_dir = move_dir / np.linalg.norm(move_dir)

        for entity in entities:
            transform = entity.get_component(Transform)
            controller = entity.get_component(PlayerController)

            # Apply movement
            speed = controller.move_speed
            velocity = move_dir * speed
            
            # Simple Euler integration
            new_pos = transform.get_world_position() + velocity * dt
            transform.set_world_position(new_pos)
