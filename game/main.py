# game_project/main.py

from aurora_engine.core.application import Application
from aurora_engine.ecs.entity import Entity
from aurora_engine.scene.transform import Transform
from aurora_engine.rendering.mesh import MeshRenderer, create_cube_mesh, create_sphere_mesh, create_plane_mesh
from aurora_engine.rendering.material import Material
from aurora_engine.rendering.shader import Shader
from game.systems.player_system import PlayerSystem
from game.systems.dialogue_system import DialogueSystem
from game.systems.world_generator import WorldGenerator
from game.ai.ai_generator import AIContentGenerator
from aurora_engine.database.db_manager import DatabaseManager
from aurora_engine.database.schema import DatabaseSchema
import numpy as np
import json
import os
from typing import Dict


class Rifted(Application):
    """
    Example RPG game built on Aurora Engine.
    This is the GAME layer - it uses the engine API.
    """

    def initialize_game(self):
        """Game-specific initialization."""
        # Initialize Database
        self.db_manager = DatabaseManager(self.config.get('database.path', 'game.db'))
        self.db_manager.connect()
        
        # Ensure Schema
        DatabaseSchema.create_tables(self.db_manager)
        
        # Initialize AI Generator
        self.ai_generator = AIContentGenerator(self.db_manager)
        
        # Initialize World Generator
        self.world_generator = WorldGenerator(self.db_manager, self.ai_generator)

        # Create player entity
        self.player = self.world.create_entity()
        player_transform = self.player.add_component(Transform())
        player_transform.set_world_position(np.array([0, 0, 0.5], dtype=np.float32)) # On ground

        # Add player visual (Blue Cube)
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
        # Pass input manager to PlayerSystem
        self.world.add_system(PlayerSystem(self.input))
        
        dialogue_system = DialogueSystem(self.ui)
        dialogue_system.ai_generator = self.ai_generator
        self.world.add_system(dialogue_system)

        # Load Initial World
        self._load_world()
        
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
            
        # Chunk Loading Logic
        if hasattr(self, 'player') and hasattr(self, 'world_generator'):
            transform = self.player.get_component(Transform)
            pos = transform.get_world_position()
            # In a real game, we'd check if we crossed a chunk boundary before calling this every frame
            # For now, let's just do it periodically or simply rely on the generator's internal checks if we add them.
            # But the generator just returns data, it doesn't instantiate.
            # We need a system to instantiate the generated regions.
            pass

    def _load_world(self):
        """Load the procedural world."""
        # 1. Get/Create Dimension
        # Tutorial Dimension (Seed 12345)
        dim = self.world_generator.get_or_create_dimension("dim_tutorial", 12345)
        print(f"Entered Dimension: {dim['name']}")
        
        # 2. Generate Initial Regions around (0,0)
        regions = self.world_generator.load_chunks_around_player("dim_tutorial", 0, 0, radius=1)
        
        # 3. Instantiate Regions
        for region in regions:
            self._instantiate_region(region)

    def _instantiate_region(self, region_data: Dict):
        """Create entities for a region."""
        # This is a simplified instantiation. In a real engine, we'd have a RegionManager system.
        entities = json.loads(region_data['entities_json'])
        
        for entity_data in entities:
            # Create Entity
            e = self.world.create_entity()
            t = e.add_component(Transform())
            t.set_world_position(np.array([entity_data['x'], entity_data['y'], entity_data['z']], dtype=np.float32))
            
            # Visuals
            if entity_data['model'] == 'rock':
                mesh = create_cube_mesh(entity_data['scale'])
                e.add_component(MeshRenderer(mesh=mesh, color=(0.5, 0.5, 0.5, 1.0))) # Grey Rock
            elif entity_data['model'] == 'tree':
                mesh = create_cube_mesh(entity_data['scale'] * 2.0) # Tall cube
                e.add_component(MeshRenderer(mesh=mesh, color=(0.2, 0.6, 0.2, 1.0))) # Green Tree
                
        # Create Ground for this region
        # 100x100 chunk
        ground = self.world.create_entity()
        gt = ground.add_component(Transform())
        # Center of chunk
        cx = region_data['coordinates_x'] * 100
        cy = region_data['coordinates_y'] * 100
        gt.set_world_position(np.array([cx, cy, 0], dtype=np.float32))
        gt.local_scale = np.array([100.0, 100.0, 1.0], dtype=np.float32)
        
        ground_mesh = create_plane_mesh(1.0, 1.0)
        # Biome color
        biome = region_data['biome_type']
        color = (0.2, 0.8, 0.2, 1.0) # Default Green
        if biome == 'Desert': color = (0.8, 0.8, 0.4, 1.0)
        elif biome == 'Volcanic': color = (0.3, 0.1, 0.1, 1.0)
        elif biome == 'Tundra': color = (0.9, 0.9, 1.0, 1.0)
        
        ground.add_component(MeshRenderer(mesh=ground_mesh, color=color))

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
            'title': 'Rifted',
        },
        'database': {
            'path': 'game.db'
        }
    }
    
    # Write config to file so Application loads it correctly
    with open("config.json", "w") as f:
        json.dump(config_data, f, indent=2)

    game = Rifted("config.json")
    game.run()
