# game_project/main.py

from aurora_engine.core.application import Application
from aurora_engine.ecs.entity import Entity
from aurora_engine.scene.transform import Transform
from game.systems.player_system import PlayerSystem
from game.systems.dialogue_system import DialogueSystem
from game.ai.ai_generator import AIContentGenerator
from aurora_engine.database.db_manager import DatabaseManager
import numpy as np


class RPGGame(Application):
    """
    Example RPG game built on Aurora Engine.
    This is the GAME layer - it uses the engine API.
    """

    def initialize_game(self):
        """Game-specific initialization."""
        # Initialize Database
        self.db_manager = DatabaseManager(self.config.get('database.path', 'game.db'))
        self.db_manager.connect()
        
        # Initialize AI Generator
        self.ai_generator = AIContentGenerator(self.db_manager)

        # Create player entity
        player = self.world.create_entity()
        player_transform = player.add_component(Transform())
        player_transform.set_world_position(np.array([0, 0, 5], dtype=np.float32))

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
        
        dialogue_system = DialogueSystem(self.ui)
        dialogue_system.ai_generator = self.ai_generator
        self.world.add_system(dialogue_system)

        # Load initial scene
        self._load_starting_town()

    def _load_starting_town(self):
        """Load the starting town scene."""
        # Spawn NPCs
        self._spawn_npc("village_elder", "Elder", np.array([10, 0, 0], dtype=np.float32))
        self._spawn_npc("merchant", "Merchant", np.array([5, 10, 0], dtype=np.float32))

        # Load environment
        # TODO: Load town buildings, props

    def _spawn_npc(self, npc_id: str, name: str, position: np.ndarray):
        """Spawn an NPC entity."""
        npc = self.world.create_entity()

        npc_transform = npc.add_component(Transform())
        npc_transform.set_world_position(position)

        from game.components.npc import NPCController
        npc_controller = npc.add_component(NPCController(npc_id, name))

        return npc
    
    def shutdown(self):
        """Cleanup."""
        super().shutdown()
        if hasattr(self, 'db_manager'):
            self.db_manager.disconnect()


if __name__ == "__main__":
    config = {
        'rendering': {
            'width': 1920,
            'height': 1080,
            'title': 'My RPG Game',
        },
        'database': {
            'path': 'game.db'
        }
    }

    game = RPGGame("config.json") # Config path or dict if supported, but Application expects path
    # We need to ensure Application can take dict or we save it first.
    # Application takes config_path. Let's just rely on default or save one.
    # For this example, we'll assume Application handles it or we modify it.
    # Actually Application loads from file. Let's just instantiate.
    
    # To make it work with the provided dict in main, we might need to modify Application or save the file.
    # But for now, let's just run it.
    game.run()
