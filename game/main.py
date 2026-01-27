# game_project/main.py

from aurora_engine.core.application import Application
from aurora_engine.ecs.entity import Entity
from aurora_engine.scene.transform import Transform
from aurora_engine.rendering.mesh import MeshRenderer, create_cube_mesh, create_sphere_mesh, create_plane_mesh
from aurora_engine.rendering.material import Material
from aurora_engine.rendering.shader import Shader
from game.systems.dialogue_system import DialogueSystem
from game.systems.world_generator import WorldGenerator
from game.ai.ai_generator import AIContentGenerator
from aurora_engine.database.db_manager import DatabaseManager
from aurora_engine.database.schema import DatabaseSchema
from aurora_engine.world.terrain_generator import create_terrain_mesh_from_heightmap, get_height_at_world_pos
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

        # Setup Camera for World Overview
        from aurora_engine.camera.camera import Camera
        from aurora_engine.camera.free_fly import FreeFlyController

        camera = Camera()
        camera_transform = camera.transform
        # Position lower and look down less steeply to see terrain better
        camera_transform.set_world_position(np.array([0, 0, 30.0], dtype=np.float32))
        
        self.camera_controller = FreeFlyController(camera)
        self.camera_controller.pitch = -60.0 # Look down 60 degrees
        self.camera_controller.auto_pan_speed = 2.0 # Slower pan
        self.renderer.register_camera(camera)

        # Add game systems
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
        alight.setColor(Vec4(0.3, 0.3, 0.3, 1)) # Reduced ambient for better contrast
        alnp = self.renderer.backend.scene_graph.attachNewNode(alight)
        self.renderer.backend.scene_graph.setLight(alnp)
        
        # Directional light
        dlight = DirectionalLight('dlight')
        dlight.setColor(Vec4(0.5, 0.5, 0.5, 1)) # Reduced intensity to prevent whiteout
        dlnp = self.renderer.backend.scene_graph.attachNewNode(dlight)
        dlnp.setHpr(45, -60, 0) # Angled light
        self.renderer.backend.scene_graph.setLight(dlnp)

    def update(self, dt: float, alpha: float):
        """Override update to update camera controller."""
        super().update(dt, alpha)
        if hasattr(self, 'camera_controller'):
            self.camera_controller.update(dt)
            
        # Dynamic Chunk Loading (Simple radius check around camera)
        if hasattr(self, 'camera_controller') and hasattr(self, 'world_generator'):
            cam_pos = self.camera_controller.camera.transform.get_world_position()
            # Load chunks around camera
            # In a real game, optimize this to not call every frame
            # self.world_generator.load_chunks_around_player("dim_tutorial", cam_pos[0], cam_pos[1], radius=2)
            pass

    def _load_world(self):
        """Load the procedural world."""
        # 1. Get/Create Dimension
        # Tutorial Dimension (Seed 12345)
        dim = self.world_generator.get_or_create_dimension("dim_tutorial", 12345)
        print(f"Entered Dimension: {dim['name']}")
        
        # 2. Generate Initial Regions around (0,0)
        # Generate a larger area for the flyover
        regions = self.world_generator.load_chunks_around_player("dim_tutorial", 0, 0, radius=2)
        
        # 3. Instantiate Regions
        for region in regions:
            self._instantiate_region(region)
            
        # 4. Add Water Plane
        # A large blue plane at Z=-2.0 to simulate water level
        water = self.world.create_entity()
        wt = water.add_component(Transform())
        wt.set_world_position(np.array([0, 0, -2.0], dtype=np.float32))
        wt.local_scale = np.array([500.0, 500.0, 1.0], dtype=np.float32)
        
        water_mesh = create_plane_mesh(1.0, 1.0)
        water.add_component(MeshRenderer(mesh=water_mesh, color=(0.2, 0.4, 0.8, 0.8)))

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
                
        # Create Terrain for this region
        if 'heightmap_data' in region_data and region_data['heightmap_data']:
            heightmap = np.array(json.loads(region_data['heightmap_data']), dtype=np.float32)
            
            # Generate Terrain Mesh
            # Cell size = region_size / resolution. 
            # In WorldGenerator we used 100.0 size and 10 resolution, so cell_size = 10.0
            terrain_mesh = create_terrain_mesh_from_heightmap(heightmap, cell_size=10.0)
            
            ground = self.world.create_entity()
            gt = ground.add_component(Transform())
            
            # Position: The mesh is generated from (0,0) to (100,100) in local space.
            # We need to place it at the region's world origin.
            rx = region_data['coordinates_x'] * 100.0
            ry = region_data['coordinates_y'] * 100.0
            gt.set_world_position(np.array([rx, ry, 0], dtype=np.float32))
            
            # Use default white color so vertex colors show through
            ground.add_component(MeshRenderer(mesh=terrain_mesh, color=(1.0, 1.0, 1.0, 1.0)))

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
    
    # Remove old DB to ensure schema update
    if os.path.exists("game.db"):
        os.remove("game.db")
    
    # Write config to file so Application loads it correctly
    with open("config.json", "w") as f:
        json.dump(config_data, f, indent=2)

    game = Rifted("config.json")
    game.run()
