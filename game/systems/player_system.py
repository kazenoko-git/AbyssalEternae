# game_project/systems/player_system.py

from aurora_engine.ecs.system import System
from aurora_engine.scene.transform import Transform
from aurora_engine.physics.rigidbody import RigidBody
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
        self.context.action_map.create_action("Jump").add_binding(InputDevice.KEYBOARD, "space")
        
        self.input_manager.set_active_context(self.context)

    def get_required_components(self):
        return [Transform, PlayerController] # RigidBody is optional but recommended

    def update(self, entities, dt):
        """Update player movement."""
        
        input_state = self.input_manager._input_state 
        
        move_input = np.zeros(3, dtype=np.float32)
        
        if self.context.action_map.is_action_active("MoveForward", input_state):
            move_input[1] += 1.0
        if self.context.action_map.is_action_active("MoveBackward", input_state):
            move_input[1] -= 1.0
        if self.context.action_map.is_action_active("MoveLeft", input_state):
            move_input[0] -= 1.0
        if self.context.action_map.is_action_active("MoveRight", input_state):
            move_input[0] += 1.0
            
        if np.linalg.norm(move_input) > 0:
            move_input = move_input / np.linalg.norm(move_input)

        jump = self.context.action_map.is_action_active("Jump", input_state)

        for entity in entities:
            transform = entity.get_component(Transform)
            controller = entity.get_component(PlayerController)
            rigidbody = entity.get_component(RigidBody)

            # Calculate movement direction relative to camera (if available)
            # For now, assume camera follows player rotation or world space
            # Let's use world space for simplicity, or transform.forward if we rotate player
            
            # If we have a rigidbody, use physics
            if rigidbody:
                # Get current velocity
                current_vel = rigidbody.velocity
                
                # Apply movement force/velocity
                # We want instant response, so setting velocity is often better for characters than force
                target_vel_x = move_input[0] * controller.move_speed
                target_vel_y = move_input[1] * controller.move_speed
                
                # Preserve Z velocity (gravity)
                new_vel = np.array([target_vel_x, target_vel_y, current_vel[2]], dtype=np.float32)
                
                # Jump
                if jump and abs(current_vel[2]) < 0.1: # Simple ground check
                     new_vel[2] = controller.jump_force
                     
                rigidbody.set_velocity(new_vel)
                
                # Rotate player to face movement direction
                if np.linalg.norm(move_input) > 0.1:
                    # Calculate yaw
                    angle = np.arctan2(move_input[0], move_input[1])
                    # Create quaternion (Z-up rotation)
                    # ... (Math util needed here, or just set rotation)
                    pass

            else:
                # Fallback to direct transform modification (no gravity)
                velocity = move_input * controller.move_speed
                new_pos = transform.get_world_position() + velocity * dt
                transform.set_world_position(new_pos)
