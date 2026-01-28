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
from game.utils.chunk_worker import generate_chunk_meshes
from game.components.fade_in import FadeInEffect
from game.systems.fade_in_system import FadeInSystem
import numpy as np
import json
import os
import time
from typing import Dict, Tuple, Set
from concurrent.futures import ThreadPoolExecutor


class WorldGenTest(Application):
    """
    Example script to test procedural world generation and terrain rendering.
    """

    def initialize_game(self):
        """Test initialization."""
        # Initialize Database (MySQL)
        # Use the config passed to Application
        db_config = self.config.get('database', {})
        
        # Fallback if config is missing (e.g. running script directly without config file)
        if not db_config:
             db_config = {
                'host': 'localhost',
                'user': 'root',
                'password': 'CeneX_1234',
                'database': 'rifted_test_db',
                'port': 3306
            }
            
        self.db_manager = DatabaseManager(db_config)
        self.db_manager.connect()
        
        # Ensure Schema
        DatabaseSchema.create_tables(self.db_manager)
        
        # Initialize AI Generator
        self.ai_generator = AIContentGenerator(self.db_manager)
        
        # Initialize World Generator
        self.world_generator = WorldGenerator(self.db_manager, self.ai_generator)
        
        # Mesh Generation Executor
        self.mesh_executor = ThreadPoolExecutor(max_workers=4)

        # Setup Flyover Camera
        camera = Camera()
        camera.transform.set_world_position(np.array([0, 0, 80.0], dtype=np.float32))
        
        self.camera_controller = FlyoverCameraController(camera)
        self.camera_controller.height = 80.0 
        self.camera_controller.speed = 25.0 
        self.camera_controller.pitch = -20.0 
        self.renderer.register_camera(camera)
        
        # Add Fade System
        self.world.add_system(FadeInSystem())
        
        # Chunk Management
        self.loaded_chunks: Dict[Tuple[int, int], list] = {} 
        self.pending_data: Dict[Tuple[int, int], object] = {} # Coords -> Future
        self.pending_meshes: Dict[Tuple[int, int], object] = {} # Coords -> Future

        self.load_radius = 6 
        self.unload_radius = 8
        self.last_chunk_check = 0.0

        # Load Test World Metadata
        self._load_world_meta()
        
        # Add basic lighting & Fog
        self._setup_lighting_and_fog()
        
        # Load Initial World (Synchronous)
        self._load_initial_world()

    def _setup_lighting_and_fog(self):
        """Setup basic scene lighting and fog."""
        from panda3d.core import AmbientLight, DirectionalLight, Vec4, Fog
        
        # Ambient light
        alight = AmbientLight('alight')
        alight.setColor(Vec4(0.4, 0.4, 0.4, 1))
        alnp = self.renderer.backend.scene_graph.attachNewNode(alight)
        self.renderer.backend.scene_graph.setLight(alnp)
        
        # Directional light
        dlight = DirectionalLight('dlight')
        dlight.setColor(Vec4(0.8, 0.8, 0.8, 1))
        dlnp = self.renderer.backend.scene_graph.attachNewNode(dlight)
        dlnp.setHpr(45, -60, 0)
        self.renderer.backend.scene_graph.setLight(dlnp)
        
        # Fog
        fog = Fog("WorldFog")
        fog.setColor(0.53, 0.8, 0.92) # Match Sky Blue background
        fog.setExpDensity(0.002) 
        self.renderer.backend.scene_graph.setFog(fog)

    def update(self, dt: float, alpha: float):
        """Override update to update camera controller."""
        super().update(dt, alpha)
        if hasattr(self, 'camera_controller'):
            self.camera_controller.update(dt)
            
            # Chunk Management (Throttled)
            self.last_chunk_check += dt
            if self.last_chunk_check > 0.5: # Check every 0.5s
                self._manage_chunks()
                self.last_chunk_check = 0.0
            else:
                # Still process futures every frame to avoid stalls
                self._process_futures()

    def _process_futures(self):
        """Process completed futures."""
        # 4. Process Stage 1 Futures (Data Gen)
        completed_data = []
        for coords, future in self.pending_data.items():
            if future.done():
                try:
                    region_data = future.result()
                    # Start Stage 2: Mesh Gen
                    mesh_future = self.mesh_executor.submit(generate_chunk_meshes, region_data)
                    self.pending_meshes[coords] = mesh_future
                except Exception as e:
                    print(f"Chunk data generation failed for {coords}: {e}")
                completed_data.append(coords)
                
        for coords in completed_data:
            del self.pending_data[coords]
                
        # 5. Process Stage 2 Futures (Mesh Gen)
        completed_meshes = []
        for coords, future in self.pending_meshes.items():
            if future.done():
                try:
                    meshes = future.result()
                    # Re-fetch region data from DB (cached) to pass to instantiate
                    region_data = self.world_generator.generate_region("dim_test", coords[0], coords[1])
                    self._instantiate_chunk(region_data, meshes, fade_in=True)
                except Exception as e:
                    print(f"Chunk mesh generation failed for {coords}: {e}")
                completed_meshes.append(coords)
                
        for coords in completed_meshes:
            del self.pending_meshes[coords]

    def _manage_chunks(self):
        """Handle loading and unloading of chunks."""
        cam_pos = self.camera_controller.camera.transform.get_world_position()
        
        # 1. Determine needed chunks
        all_needed = self.world_generator.get_chunks_in_radius(cam_pos[0], cam_pos[1], self.load_radius)
        all_needed.sort(key=lambda c: (c[0]*100 - cam_pos[0])**2 + (c[1]*100 - cam_pos[1])**2)
        needed_chunks = set(all_needed)
        
        # 2. Unload distant chunks
        chunks_to_unload = []
        for coords in self.loaded_chunks:
            chunk_world_x = coords[0] * 100.0
            chunk_world_y = coords[1] * 100.0
            dist = np.sqrt((chunk_world_x - cam_pos[0])**2 + (chunk_world_y - cam_pos[1])**2)
            
            if dist > self.unload_radius * 100.0:
                chunks_to_unload.append(coords)
                
        for coords in chunks_to_unload:
            self._unload_chunk(coords)
            
        # 3. Load new chunks (Stage 1)
        max_concurrent_loads = 16 
        current_loads = len(self.pending_data) + len(self.pending_meshes)
        
        for coords in needed_chunks:
            if current_loads >= max_concurrent_loads:
                break
                
            if coords not in self.loaded_chunks and coords not in self.pending_data and coords not in self.pending_meshes:
                self._request_chunk_load(coords)
                current_loads += 1
        
        # Process futures immediately too
        self._process_futures()

    def _request_chunk_load(self, coords: Tuple[int, int]):
        """Start async generation."""
        future = self.world_generator.generate_region_async("dim_test", coords[0], coords[1])
        self.pending_data[coords] = future

    def _unload_chunk(self, coords: Tuple[int, int]):
        """Destroy entities in a chunk."""
        if coords in self.loaded_chunks:
            entities = self.loaded_chunks[coords]
            for entity in entities:
                self.world.destroy_entity(entity)
            del self.loaded_chunks[coords]

    def _load_world_meta(self):
        """Load/Create dimension metadata."""
        seed = 12345 
        dim = self.world_generator.get_or_create_dimension("dim_test", seed)
        print(f"Dimension: {dim['name']}")

    def _load_initial_world(self):
        """Load the initial area synchronously."""
        print("Loading initial world...")
        # Load same radius as runtime to avoid gaps
        regions = self.world_generator.load_chunks_around_player("dim_test", 0, 0, radius=self.load_radius)
        
        for region in regions:
            # We need meshes. Generate them synchronously here for simplicity, or reuse worker logic.
            # Since this is init, blocking is fine.
            meshes = generate_chunk_meshes(region)
            self._instantiate_chunk(region, meshes, fade_in=False) # No fade for initial load

    def _instantiate_chunk(self, region_data: Dict, meshes: Dict, fade_in: bool = True):
        """Create entities for a region using pre-generated meshes."""
        coords = (region_data['coordinates_x'], region_data['coordinates_y'])
        
        if coords in self.loaded_chunks:
            return
            
        chunk_entities = []
        
        # Props
        for entity_data, mesh in meshes['props']:
            e = self.world.create_entity()
            t = e.add_component(Transform())
            t.set_world_position(np.array([entity_data['x'], entity_data['y'], entity_data['z']], dtype=np.float32))
            
            # Visuals
            e.add_component(MeshRenderer(mesh=mesh, color=(1.0, 1.0, 1.0, 1.0)))
            if fade_in:
                e.add_component(FadeInEffect(duration=1.5))
            
            # Colliders
            if entity_data['model'] == 'rock':
                e.add_component(Collider(MeshCollider(mesh, convex=True)))
            elif entity_data['model'] == 'tree':
                scale = entity_data.get('scale', 1.0)
                e.add_component(Collider(BoxCollider(np.array([0.5 * scale, 0.5 * scale, 4.0 * scale], dtype=np.float32))))
            
            chunk_entities.append(e)
                
        # Terrain
        if meshes['terrain']:
            ground = self.world.create_entity()
            gt = ground.add_component(Transform())
            
            rx = region_data['coordinates_x'] * 100.0
            ry = region_data['coordinates_y'] * 100.0
            gt.set_world_position(np.array([rx, ry, 0], dtype=np.float32))
            
            ground.add_component(MeshRenderer(mesh=meshes['terrain'], color=(1.0, 1.0, 1.0, 1.0)))
            if fade_in:
                ground.add_component(FadeInEffect(duration=1.5))
            
            # Heightfield Collider needs raw heightmap data
            if 'heightmap_data' in region_data:
                heightmap = np.array(json.loads(region_data['heightmap_data']), dtype=np.float32)
                ground.add_component(Collider(HeightfieldCollider(heightmap)))
            
            chunk_entities.append(ground)
            
        # Water Plane
        water = self.world.create_entity()
        wt = water.add_component(Transform())
        rx = region_data['coordinates_x'] * 100.0
        ry = region_data['coordinates_y'] * 100.0
        wt.set_world_position(np.array([rx + 50.0, ry + 50.0, -2.0], dtype=np.float32))
        wt.local_scale = np.array([100.0, 100.0, 1.0], dtype=np.float32)
        
        water_mesh = create_plane_mesh(1.0, 1.0)
        water.add_component(MeshRenderer(mesh=water_mesh, color=(0.2, 0.4, 0.8, 0.8)))
        water.add_component(Collider(BoxCollider(np.array([100.0, 100.0, 1.0], dtype=np.float32))))
        if fade_in:
            water.add_component(FadeInEffect(duration=1.5))
        
        chunk_entities.append(water)
        
        self.loaded_chunks[coords] = chunk_entities
    
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
            'host': 'localhost',
            'user': 'root',
            'password': 'CeneX_1234', # Set your MySQL password here
            'database': 'rifted_test_db',
            'port': 3306
        }
    }
    
    with open("test_config.json", "w") as f:
        json.dump(config_data, f, indent=2)

    app = WorldGenTest("test_config.json")
    app.run()
