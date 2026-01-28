# game_project/main.py

from aurora_engine.core.application import Application
from aurora_engine.ecs.entity import Entity
from aurora_engine.scene.transform import Transform
from aurora_engine.rendering.mesh import MeshRenderer, create_cube_mesh
from game.systems.player_system import PlayerSystem
from game.systems.dialogue_system import DialogueSystem
from game.ai.ai_generator import AIContentGenerator
from aurora_engine.database.db_manager import DatabaseManager
from aurora_engine.database.schema import DatabaseSchema
import numpy as np
import json
import os


class Rifted(Application):
    """
    The Main RPG Game Application.
    """

    def initialize_game(self):
        """Game-specific initialization."""
        # Initialize Database (MySQL)
        db_config = self.config.get('database', {})
        self.db_manager = DatabaseManager(db_config)
        self.db_manager.connect()
        
        # Ensure Schema
        DatabaseSchema.create_tables(self.db_manager)
        
        # Initialize AI Generator
        self.ai_generator = AIContentGenerator(self.db_manager)

        # Create player entity
        self.player = self.world.create_entity()
        player_transform = self.player.add_component(Transform())
        player_transform.set_world_position(np.array([0, 0, 2.0], dtype=np.float32))

        # Add player visual (Blue Cube placeholder)
        player_mesh = create_cube_mesh(1.0)
        self.player.add_component(MeshRenderer(mesh=player_mesh, color=(0.2, 0.4, 0.8, 1.0)))

        # Add player-specific components
        from game.components.player import PlayerController
        self.player.add_component(PlayerController())

        # Setup camera to follow player
        from aurora_engine.camera.camera import Camera
        from aurora_engine.camera.third_person import ThirdPersonController

        camera = Camera()
        self.camera_controller = ThirdPersonController(camera, player_transform)
        self.renderer.register_camera(camera)

        # Add game systems
        self.world.add_system(PlayerSystem(self.input))
        
        dialogue_system = DialogueSystem(self.ui)
        dialogue_system.ai_generator = self.ai_generator
        self.world.add_system(dialogue_system)

        # TODO: Load actual game world / save file
        # self._load_game_world()
        
        # Add basic lighting
        self._setup_lighting()

    def _setup_lighting(self):
        """Setup basic scene lighting."""
        from panda3d.core import AmbientLight, DirectionalLight, Vec4
        
        # Ambient light
        alight = AmbientLight('alight')
        alight.setColor(Vec4(0.3, 0.3, 0.3, 1))
        alnp = self.renderer.backend.scene_graph.attachNewNode(alight)
        self.renderer.backend.scene_graph.setLight(alnp)
        
        # Directional light
        dlight = DirectionalLight('dlight')
        dlight.setColor(Vec4(0.8, 0.8, 0.8, 1))
        dlnp = self.renderer.backend.scene_graph.attachNewNode(dlight)
        dlnp.setHpr(45, -60, 0)
        self.renderer.backend.scene_graph.setLight(dlnp)

    def update(self, dt: float, alpha: float):
        """Override update to update camera controller."""
        super().update(dt, alpha)
        if hasattr(self, 'camera_controller'):
            self.camera_controller.update(dt)
    
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
            'title': 'Rifted',
        },
        'database': {
            'host': 'localhost',
            'user': 'root',
            'password': '', # Set your MySQL password here
            'database': 'rifted_db',
            'port': 3306
        }
    }

    # Write config to file so Application loads it correctly
    with open("config.json", "w") as f:
        json.dump(config_data, f, indent=2)

    game = Rifted("config.json")
    game.run()
