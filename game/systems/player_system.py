# game_project/systems/player_system.py

from aurora_engine.ecs.system import System
from aurora_engine.scene.transform import Transform
from aurora_engine.physics.rigidbody import RigidBody
from game.components.player import PlayerController
from aurora_engine.input.input_manager import InputManager
from aurora_engine.input.action_map import InputDevice
from aurora_engine.core.logging import get_logger
import numpy as np


class PlayerSystem(System):
    """
    Player movement system.
    This is GAME logic built on ENGINE components.
    """
    
    def __init__(self, input_manager: InputManager):
        super().__init__()
        self.input_manager = input_manager
        self.priority = -10 # Run before physics
        self.logger = get_logger()
        self.logger.info("PlayerSystem initialized")

    def get_required_components(self):
        return [Transform, PlayerController, RigidBody]

    def update(self, entities, dt):
        """Update player movement."""
        
        move_input = np.zeros(3, dtype=np.float32)
        
        if self.input_manager.is_key_down("w"):
            move_input[1] += 1.0
        if self.input_manager.is_key_down("s"):
            move_input[1] -= 1.0
        if self.input_manager.is_key_down("a"):
            move_input[0] -= 1.0
        if self.input_manager.is_key_down("d"):
            move_input[0] += 1.0
            
        if np.linalg.norm(move_input) > 0:
            move_input = move_input / np.linalg.norm(move_input)
            # self.logger.debug(f"Player input: {move_input}") # Verbose

        jump = self.input_manager.is_key_down("space")
        if jump:
            # self.logger.debug("Player jump input")
            pass

        for entity in entities:
            transform = entity.get_component(Transform)
            controller = entity.get_component(PlayerController)
            rigidbody = entity.get_component(RigidBody)

            # Get current velocity
            current_vel = rigidbody.velocity
            
            # Apply movement force/velocity
            target_vel_x = move_input[0] * controller.move_speed
            target_vel_y = move_input[1] * controller.move_speed
            
            # Preserve Z velocity (gravity)
            new_vel = np.array([target_vel_x, target_vel_y, current_vel[2]], dtype=np.float32)
            
            # Jump
            if jump and abs(current_vel[2]) < 0.1: # Simple ground check
                 new_vel[2] = controller.jump_force
                 self.logger.debug("Player jumping")
            
            # Only set if changed or moving to ensure we don't override physics unnecessarily
            # But we need to override X/Y friction
            rigidbody.set_velocity(new_vel)
            
            # Rotate player to face movement direction
            if np.linalg.norm(move_input) > 0.1:
                # Calculate yaw
                angle = np.arctan2(move_input[0], move_input[1])
                # Create quaternion (Z-up rotation)
                # ... (Math util needed here, or just set rotation)
                pass
