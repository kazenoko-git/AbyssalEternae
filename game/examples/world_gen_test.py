# game/examples/world_gen_test.py

from aurora_engine.core.application import Application
from aurora_engine.ecs.entity import Entity
from aurora_engine.scene.transform import Transform
from aurora_engine.rendering.mesh import MeshRenderer, create_cube_mesh, create_sphere_mesh, create_plane_mesh
from game.systems.world_generator import WorldGenerator
from game.ai.ai_generator import AIContentGenerator
from aurora_engine.database.db_manager import DatabaseManager
from aurora_engine.database.schema import DatabaseSchema
from game.utils.terrain import create_terrain_mesh_from_heightmap
from game.utils.tree_generator import create_procedural_tree_mesh
from game.utils.rock_generator import create_procedural_rock_mesh
from game.controllers.flyover_camera import FlyoverCameraController
from aurora_engine.camera.camera import Camera
from aurora_engine.physics.collider import HeightfieldCollider, MeshCollider, BoxCollider
from aurora_engine.physics.collider import Collider
from game.utils.chunk_worker import generate_chunk_meshes
from game.components.fade_in import FadeInEffect
from game.systems.fade_in_system import FadeInSystem
from aurora_engine.core.logging import get_logger
import numpy as np
import json
import os
import time
import random
from typing import Dict, Tuple, Set, List
from concurrent.futures import ThreadPoolExecutor, Future

logger = get_logger()

class WorldGenTest(Application):
    """
    Example script to test procedural world generation and terrain rendering.
    """

    def initialize_game(self):
        """Test initialization."""
        logger.info("Initializing WorldGenTest")
        # Initialize Database (MySQL)
        db_config = self.config.get('database', {})
        if not db_config:
             db_config = {
                'host': 'localhost',
                'user': 'root',
                'password': '',
                'database': 'rifted_test_db',
                'port': 3306
            }
            
        self.db_manager = DatabaseManager(db_config)
        self.db_manager.connect()
        
        # Reset DB for fresh test
        DatabaseSchema.drop_tables(self.db_manager)
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
        self.chunk_entities: Dict[Tuple[int, int], List[Entity]] = {}
        self.chunk_states: Dict[Tuple[int, int], str] = {} # UNLOADED, PENDING_DATA, PENDING_MESH, LOADED
        self.chunk_futures: Dict[Tuple[int, int], Future] = {}

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
        from panda3d.core import AmbientLight, DirectionalLight, Vec4, Fog
        alight = AmbientLight('alight')
        alight.setColor(Vec4(0.4, 0.4, 0.4, 1))
        alnp = self.renderer.backend.scene_graph.attachNewNode(alight)
        self.renderer.backend.scene_graph.setLight(alnp)
        
        dlight = DirectionalLight('dlight')
        dlight.setColor(Vec4(0.8, 0.8, 0.8, 1))
        dlnp = self.renderer.backend.scene_graph.attachNewNode(dlight)
        dlnp.setHpr(45, -60, 0)
        self.renderer.backend.scene_graph.setLight(dlnp)
        
        fog = Fog("WorldFog")
        fog.setColor(0.53, 0.8, 0.92)
        fog.setExpDensity(0.002) 
        self.renderer.backend.scene_graph.setFog(fog)

    def update(self, dt: float, alpha: float):
        super().update(dt, alpha)
        if hasattr(self, 'camera_controller'):
            self.camera_controller.update(dt)
            
            self.last_chunk_check += dt
            if self.last_chunk_check > 0.5:
                self._manage_chunks()
                self.last_chunk_check = 0.0
            
            self._process_futures()

    def _process_futures(self):
        completed = []
        for coords, future in self.chunk_futures.items():
            if future.done():
                try:
                    result = future.result()
                    state = self.chunk_states.get(coords)
                    
                    if state == "PENDING_DATA":
                        # Data is ready, start mesh generation
                        self.chunk_states[coords] = "PENDING_MESH"
                        mesh_future = self.mesh_executor.submit(generate_chunk_meshes, result)
                        self.chunk_futures[coords] = mesh_future # Replace future
                    
                    elif state == "PENDING_MESH":
                        # Meshes are ready, instantiate
                        region_data = self.world_generator.generate_region("dim_test", coords[0], coords[1])
                        self._instantiate_chunk(region_data, result, fade_in=True)
                        self.chunk_states[coords] = "LOADED"
                        completed.append(coords)

                except Exception as e:
                    logger.error(f"Generation failed for chunk {coords}: {e}")
                    # Reset state to allow retry
                    if coords in self.chunk_states:
                        del self.chunk_states[coords]
                    completed.append(coords)
        
        for coords in completed:
            if coords in self.chunk_futures:
                del self.chunk_futures[coords]

    def _manage_chunks(self):
        cam_pos = self.camera_controller.camera.transform.get_world_position()
        cam_dir = self.camera_controller.direction
        
        all_needed = self.world_generator.get_chunks_in_radius(cam_pos[0], cam_pos[1], self.load_radius)
        
        def chunk_priority(coords):
            chunk_world_x = coords[0] * 100.0
            chunk_world_y = coords[1] * 100.0
            to_chunk = np.array([chunk_world_x - cam_pos[0], chunk_world_y - cam_pos[1], 0.0])
            dist_sq = np.dot(to_chunk, to_chunk)
            if dist_sq < 1: return -1000000
            dist = np.sqrt(dist_sq)
            to_chunk /= dist
            dot = np.dot(to_chunk, cam_dir)
            return dist - (dot * 200.0)
            
        all_needed.sort(key=chunk_priority)
        
        # Unload distant chunks
        chunks_to_unload = []
        for coords in self.chunk_states:
            if self.chunk_states.get(coords) == "LOADED":
                chunk_world_x = coords[0] * 100.0
                chunk_world_y = coords[1] * 100.0
                dist = np.sqrt((chunk_world_x - cam_pos[0])**2 + (chunk_world_y - cam_pos[1])**2)
                if dist > self.unload_radius * 100.0:
                    chunks_to_unload.append(coords)
        
        for coords in chunks_to_unload:
            self._unload_chunk(coords)
            
        # Load new chunks
        max_concurrent_loads = 16
        for coords in all_needed:
            if len(self.chunk_futures) >= max_concurrent_loads:
                break
            if coords not in self.chunk_states:
                self._request_chunk_load(coords)

    def _request_chunk_load(self, coords: Tuple[int, int]):
        self.chunk_states[coords] = "PENDING_DATA"
        future = self.world_generator.generate_region_async("dim_test", coords[0], coords[1])
        self.chunk_futures[coords] = future

    def _unload_chunk(self, coords: Tuple[int, int]):
        if coords in self.chunk_entities:
            for entity in self.chunk_entities[coords]:
                self.world.destroy_entity(entity)
            del self.chunk_entities[coords]
        if coords in self.chunk_states:
            del self.chunk_states[coords]

    def _load_world_meta(self):
        seed = random.randrange(1,9999999)
        dim = self.world_generator.get_or_create_dimension("dim_test", seed)
        logger.info(f"Dimension: {dim['name']} (Seed: {seed})")

    def _load_initial_world(self):
        logger.info("Loading initial world...")
        regions = self.world_generator.load_chunks_around_player("dim_test", 0, 0, radius=self.load_radius)
        for region in regions:
            meshes = generate_chunk_meshes(region)
            self._instantiate_chunk(region, meshes, fade_in=False)

    def _instantiate_chunk(self, region_data: Dict, meshes: Dict, fade_in: bool = True):
        coords = (region_data['coordinates_x'], region_data['coordinates_y'])
        if coords in self.chunk_entities: return
            
        chunk_entities = []
        
        for entity_data, mesh in meshes['props']:
            e = self.world.create_entity()
            t = e.add_component(Transform())
            t.set_world_position(np.array([entity_data['x'], entity_data['y'], entity_data['z']], dtype=np.float32))
            e.add_component(MeshRenderer(mesh=mesh, color=(1.0, 1.0, 1.0, 1.0)))
            if fade_in: e.add_component(FadeInEffect(duration=1.5))
            
            if entity_data['type'] == 'prop':
                if entity_data['model'] == 'rock': e.add_component(Collider(MeshCollider(mesh, convex=True)))
                elif entity_data['model'] == 'tree':
                    scale = entity_data.get('scale', 1.0)
                    e.add_component(Collider(BoxCollider(np.array([0.5 * scale, 0.5 * scale, 4.0 * scale], dtype=np.float32))))
            elif entity_data['type'] == 'structure':
                e.add_component(Collider(BoxCollider(np.array([4.0, 3.0, 3.0], dtype=np.float32))))
            
            chunk_entities.append(e)
                
        if meshes['terrain']:
            ground = self.world.create_entity()
            gt = ground.add_component(Transform())
            rx, ry = region_data['coordinates_x'] * 100.0, region_data['coordinates_y'] * 100.0
            gt.set_world_position(np.array([rx, ry, 0], dtype=np.float32))
            ground.add_component(MeshRenderer(mesh=meshes['terrain'], color=(1.0, 1.0, 1.0, 1.0)))
            if fade_in: ground.add_component(FadeInEffect(duration=1.5))
            
            if 'heightmap_data' in region_data:
                heightmap = np.array(json.loads(region_data['heightmap_data']), dtype=np.float32)
                ground.add_component(Collider(HeightfieldCollider(heightmap)))
            
            chunk_entities.append(ground)
            
        water = self.world.create_entity()
        wt = water.add_component(Transform())
        rx, ry = region_data['coordinates_x'] * 100.0, region_data['coordinates_y'] * 100.0
        wt.set_world_position(np.array([rx + 50.0, ry + 50.0, -2.0], dtype=np.float32))
        wt.local_scale = np.array([100.0, 100.0, 1.0], dtype=np.float32)
        water.add_component(MeshRenderer(mesh=create_plane_mesh(1.0, 1.0), color=(0.2, 0.4, 0.8, 0.8)))
        water.add_component(Collider(BoxCollider(np.array([100.0, 100.0, 1.0], dtype=np.float32))))
        if fade_in: water.add_component(FadeInEffect(duration=1.5))
        
        chunk_entities.append(water)
        
        self.chunk_entities[coords] = chunk_entities
    
    def shutdown(self):
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
            'password': 'CeneX_1234',
            'database': 'rifted_test_db',
            'port': 3306
        }
    }
    
    with open("test_config.json", "w") as f:
        json.dump(config_data, f, indent=2)

    app = WorldGenTest("test_config.json")
    app.run()
