# game_project/main.py

from aurora_engine.core.application import Application
from aurora_engine.ecs.entity import Entity
from aurora_engine.scene.transform import Transform
from game.systems.player_system import PlayerSystem
from game.systems.dialogue_system import DialogueSystem
import numpy as np


class RPGGame(Application):
    """
    Example RPG game built on Aurora Engine.
    This is the GAME layer - it uses the engine API.
    """

    def initialize_game(self):
        """Game-specific initialization."""
        # Create player entity
        player = self.world.create_entity()
        player_transform = player.add_component(Transform())
        player_transform.set_world_position(np.array([0, 0, 5]))

        # Add player-specific components
        from game.components.player import PlayerController
        player.add_component(PlayerController())

        # Setup camera to follow player
        from aurora_engine.camera.camera import Camera
        from aurora_engine.camera.third_person import ThirdPersonController

        camera = Camera()
        camera_controller = ThirdPersonController(camera, player_transform)
        self.renderer.register_camera(camera)

        # Add game systems
        self.world.add_system(PlayerSystem())
        self.world.add_system(DialogueSystem(self.ui))

        # Load initial scene
        self._load_starting_town()

    def _load_starting_town(self):
        """Load the starting town scene."""
        # Spawn NPCs
        self._spawn_npc("village_elder", np.array([10, 0, 0]))
        self._spawn_npc("merchant", np.array([5, 10, 0]))

        # Load environment
        # TODO: Load town buildings, props

    def _spawn_npc(self, npc_id: str, position: np.ndarray):
        """Spawn an NPC entity."""
        npc = self.world.create_entity()

        npc_transform = npc.add_component(Transform())
        npc_transform.set_world_position(position)

        from game.components.npc import NPCController
        npc_controller = npc.add_component(NPCController(npc_id))

        return npc


if __name__ == "__main__":
    config = {
        'rendering': {
            'width': 1920,
            'height': 1080,
            'title': 'My RPG Game',
        }
    }

    game = RPGGame(config)
    game.run()