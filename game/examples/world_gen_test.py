# game/examples/world_gen_test.py

from aurora_engine.core.application import Application
from aurora_engine.ecs.entity import Entity
from aurora_engine.scene.transform import Transform
from aurora_engine.rendering.mesh import MeshRenderer, create_cube_mesh, create_sphere_mesh, create_plane_mesh
from game.systems.world_generator import WorldGenerator
from game.ai.ai_generator import AIContentGenerator
from aurora_engine.database.db_manager import DatabaseManager
from aurora_engine.database.schema import DatabaseSchema
from game.utils.terrain import create_terrain_mesh_from_heightmap, get_height_at_world_pos
from game.utils.tree_generator import create_procedural_tree_mesh
from game.utils.rock_generator import create_procedural_rock_mesh
from game.controllers.flyover_camera import FlyoverCameraController
from aurora_engine.camera.camera import Camera
from aurora_engine.physics.collider import HeightfieldCollider, MeshCollider, BoxCollider
from aurora_engine.physics.collider import Collider
import numpy as np
import json
import os
import time
from typing import Dict


class WorldGenTest(Application):
    """
    Example script to test procedural world generation and terrain rendering.
    """

    def initialize_game(self):
        """Test initialization."""
        # Initialize Database (Test DB)
        db_path = 'world_gen_test.db'
        if os.path.exists(db_path):
            os.remove(db_path)
            
        self.db_manager = DatabaseManager(db_path)
        self.db_manager.connect()
        
        # Ensure Schema
        DatabaseSchema.create_tables(self.db_manager)
        
        # Initialize AI Generator
        self.ai_generator = AIContentGenerator(self.db_manager)
        
        # Initialize World Generator
        self.world_generator = WorldGenerator(self.db_manager, self.ai_generator)

        # Setup Flyover Camera
        camera = Camera()
        # Start higher up
        camera.transform.set_world_position(np.array([0, 0, 80.0], dtype=np.float32))
        
        self.camera_controller = FlyoverCameraController(camera)
        self.camera_controller.height = 80.0 
        self.camera_controller.speed = 15.0
        self.camera_controller.pitch = -15.0 # Look forward more
        self.renderer.register_camera(camera)

        # Load Test World
        self._load_world()
        
        # Add basic lighting
        self._setup_lighting()
        
        # Track loaded chunks to avoid re-instantiating
        self.loaded_chunk_coords = set()

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
        dlight.setColor(Vec4(0.9, 0.9, 0.9, 1))
        dlnp = self.renderer.backend.scene_graph.attachNewNode(dlight)
        dlnp.setHpr(45, -60, 0)
        self.renderer.backend.scene_graph.setLight(dlnp)

    def update(self, dt: float, alpha: float):
        """Override update to update camera controller."""
        super().update(dt, alpha)
        if hasattr(self, 'camera_controller'):
            self.camera_controller.update(dt)
            
            # Dynamic Chunk Loading
            cam_pos = self.camera_controller.camera.transform.get_world_position()
            # Increase load radius to see horizon
            regions = self.world_generator.load_chunks_around_player("dim_test", cam_pos[0], cam_pos[1], radius=4)
            
            for region in regions:
                coords = (region['coordinates_x'], region['coordinates_y'])
                if coords not in self.loaded_chunk_coords:
                    self._instantiate_region(region)
                    self.loaded_chunk_coords.add(coords)

    def _load_world(self):
        """Load the procedural world."""
        # 1. Get/Create Dimension with Random Seed
        seed = int(time.time())
        dim = self.world_generator.get_or_create_dimension("dim_test", seed)
        print(f"Generated Dimension: {dim['name']} (Seed: {seed})")
        
        # Initial load handled by update loop now

    def _instantiate_region(self, region_data: Dict):
        """Create entities for a region."""
        entities = json.loads(region_data['entities_json'])
        biome = region_data.get('biome_type', 'Forest')
        
        for entity_data in entities:
            e = self.world.create_entity()
            t = e.add_component(Transform())
            t.set_world_position(np.array([entity_data['x'], entity_data['y'], entity_data['z']], dtype=np.float32))
            
            seed = entity_data.get('seed', 0)
            scale = entity_data.get('scale', 1.0)
            
            if entity_data['model'] == 'rock':
                # Use Procedural Rock Generator
                mesh = create_procedural_rock_mesh(seed, scale=scale)
                # Rock mesh has vertex colors (grey variations), use white node color
                e.add_component(MeshRenderer(mesh=mesh, color=(1.0, 1.0, 1.0, 1.0)))
                # Add Mesh Collider (Convex Hull)
                e.add_component(Collider(MeshCollider(mesh, convex=True)))
                
            elif entity_data['model'] == 'tree':
                # Use Procedural Tree Generator with Biome variation
                tree_type = "Oak"
                if biome == "Tundra": tree_type = "Pine"
                elif biome == "Swamp": tree_type = "Willow"
                
                mesh = create_procedural_tree_mesh(seed, height=4.0 * scale, radius=0.5 * scale, tree_type=tree_type)
                e.add_component(MeshRenderer(mesh=mesh, color=(1.0, 1.0, 1.0, 1.0)))
                # Add Box Collider for Trunk (Simplified)
                e.add_component(Collider(BoxCollider(np.array([0.5 * scale, 0.5 * scale, 4.0 * scale], dtype=np.float32))))
                
        # Create Terrain
        if 'heightmap_data' in region_data and region_data['heightmap_data']:
            heightmap = np.array(json.loads(region_data['heightmap_data']), dtype=np.float32)
            # Use higher resolution for mesh generation if available
            terrain_mesh = create_terrain_mesh_from_heightmap(heightmap, cell_size=100.0 / (heightmap.shape[0]-1))
            
            ground = self.world.create_entity()
            gt = ground.add_component(Transform())
            
            rx = region_data['coordinates_x'] * 100.0
            ry = region_data['coordinates_y'] * 100.0
            gt.set_world_position(np.array([rx, ry, 0], dtype=np.float32))
            
            # Use default white color so vertex colors show through
            ground.add_component(MeshRenderer(mesh=terrain_mesh, color=(1.0, 1.0, 1.0, 1.0)))
            
            # Add Heightfield Collider
            ground.add_component(Collider(HeightfieldCollider(heightmap)))
            
        # Add Water Plane for this chunk (simplified, just a plane at Z=-2)
        # In a real game, we'd have a single infinite water plane or shader
        water = self.world.create_entity()
        wt = water.add_component(Transform())
        rx = region_data['coordinates_x'] * 100.0
        ry = region_data['coordinates_y'] * 100.0
        wt.set_world_position(np.array([rx + 50.0, ry + 50.0, -2.0], dtype=np.float32)) # Center of chunk
        wt.local_scale = np.array([100.0, 100.0, 1.0], dtype=np.float32)
        
        water_mesh = create_plane_mesh(1.0, 1.0)
        water.add_component(MeshRenderer(mesh=water_mesh, color=(0.2, 0.4, 0.8, 0.8)))
        water.add_component(Collider(BoxCollider(np.array([100.0, 100.0, 1.0], dtype=np.float32))))
    
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
            'title': 'World Gen Test',
        },
        'database': {
            'path': 'world_gen_test.db'
        }
    }
    
    with open("test_config.json", "w") as f:
        json.dump(config_data, f, indent=2)

    app = WorldGenTest("test_config.json")
    app.run()
