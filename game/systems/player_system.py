# game_project/systems/player_system.py

from aurora_engine.ecs.system import System
from aurora_engine.scene.transform import Transform
from game.components.player import PlayerController
import numpy as np


class PlayerSystem(System):
    """
    Player movement system.
    This is GAME logic built on ENGINE components.
    """

    def get_required_components(self):
        return [Transform, PlayerController]

    def update(self, entities, dt):
        """Update player movement."""
        from aurora_engine.input.input_manager import InputManager

        for entity in entities:
            transform = entity.get_component(Transform)
            controller = entity.get_component(PlayerController)

            # Get input (from engine's input system)
            # This would connect to the actual InputManager

            # Move player
            velocity = np.array([0.0, 0.0, 0.0], dtype=np.float32)

            # TODO: Read input actions
            # TODO: Apply velocity to transform

            transform.set_world_position(transform.get_world_position() + velocity * dt)