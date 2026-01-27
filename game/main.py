# game_project/main.py

from aurora_engine.core.application import Application
from aurora_engine.ecs.entity import Entity
from aurora_engine.scene.transform import Transform
from aurora_engine.rendering.mesh import MeshRenderer, create_cube_mesh, create_sphere_mesh, create_plane_mesh
from aurora_engine.rendering.material import Material
from aurora_engine.rendering.shader import Shader
from game.systems.player_system import PlayerSystem
from game.systems.dialogue_system import DialogueSystem
from game.ai.ai_generator import AIContentGenerator
from aurora_engine.database.db_manager import DatabaseManager
import numpy as np
import json
import os


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
        player_transform.set_world_position(np.array([0, 0, 0.5], dtype=np.float32)) # On ground

        # Add player visual (Blue Cube)
        player_mesh = create_cube_mesh(1.0)
        player.add_component(MeshRenderer(mesh=player_mesh, color=(0.2, 0.4, 0.8, 1.0)))

        # Add player-specific components
        from game.components.player import PlayerController
        player.add_component(PlayerController())

        # Setup camera to follow player
        from aurora_engine.camera.camera import Camera
        from aurora_engine.camera.third_person import ThirdPersonController

        camera = Camera()
        self.camera_controller = ThirdPersonController(camera, player_transform)
        self.renderer.register_camera(camera)

        # Add game systems
        self.world.add_system(PlayerSystem())
        
        dialogue_system = DialogueSystem(self.ui)
        dialogue_system.ai_generator = self.ai_generator
        self.world.add_system(dialogue_system)

        # Load initial scene
        self._load_starting_town()
        
        # Add basic lighting
        self._setup_lighting()

    def _setup_lighting(self):
        """Setup basic scene lighting."""
        from panda3d.core import AmbientLight, DirectionalLight, Vec4
        
        # Ambient light
        alight = AmbientLight('alight')
        alight.setColor(Vec4(0.4, 0.4, 0.4, 1)) # Brighter ambient
        alnp = self.renderer.backend.scene_graph.attachNewNode(alight)
        self.renderer.backend.scene_graph.setLight(alnp)
        
        # Directional light
        dlight = DirectionalLight('dlight')
        dlight.setColor(Vec4(0.8, 0.8, 0.8, 1))
        dlnp = self.renderer.backend.scene_graph.attachNewNode(dlight)
        dlnp.setHpr(45, -60, 0) # Angled light
        self.renderer.backend.scene_graph.setLight(dlnp)

    def update(self, dt: float, alpha: float):
        """Override update to update camera controller."""
        super().update(dt, alpha)
        if hasattr(self, 'camera_controller'):
            self.camera_controller.update(dt)

    def _load_starting_town(self):
        """Load the starting town scene."""
        # Spawn NPCs
        self._spawn_npc("village_elder", "Elder", np.array([5, 0, 0.5], dtype=np.float32), (0.8, 0.2, 0.2, 1.0)) # Red
        self._spawn_npc("merchant", "Merchant", np.array([0, 5, 0.5], dtype=np.float32), (0.2, 0.8, 0.2, 1.0)) # Green

        # Load environment (Ground plane)
        ground = self.world.create_entity()
        ground_transform = ground.add_component(Transform())
        ground_transform.set_world_position(np.array([0, 0, 0], dtype=np.float32))
        ground_transform.local_scale = np.array([50.0, 50.0, 1.0], dtype=np.float32) # Scale plane (X, Y)
        
        ground_mesh = create_plane_mesh(1.0, 1.0)
        ground.add_component(MeshRenderer(mesh=ground_mesh, color=(0.5, 0.5, 0.5, 1.0))) # Grey ground

    def _spawn_npc(self, npc_id: str, name: str, position: np.ndarray, color=(1,1,1,1)):
        """Spawn an NPC entity."""
        npc = self.world.create_entity()

        npc_transform = npc.add_component(Transform())
        npc_transform.set_world_position(position)
        
        # Add NPC visual
        npc_mesh = create_sphere_mesh(0.5)
        npc.add_component(MeshRenderer(mesh=npc_mesh, color=color))

        from game.components.npc import NPCController
        npc_controller = npc.add_component(NPCController(npc_id, name))

        return npc
    
    def shutdown(self):
        """Cleanup."""
        super().shutdown()
        if hasattr(self, 'db_manager'):
            self.db_manager.disconnect()


if __name__ == "__main__":
    config_data = {
        'rendering': {
            'width': 1280,
            'height': 720,
            'title': 'My RPG Game',
        },
        'database': {
            'path': 'game.db'
        }
    }
    
    # Write config to file so Application loads it correctly
    with open("config.json", "w") as f:
        json.dump(config_data, f, indent=2)

    game = RPGGame("config.json")
    game.run()
