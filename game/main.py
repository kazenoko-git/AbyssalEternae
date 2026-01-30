# game_project/main.py

from aurora_engine.core.application import Application
from aurora_engine.ecs.entity import Entity
from aurora_engine.scene.transform import Transform
from aurora_engine.rendering.mesh import MeshRenderer, create_cube_mesh, create_plane_mesh, create_capsule_mesh
from game.systems.player_system import PlayerSystem
from game.systems.dialogue_system import DialogueSystem
from game.systems.world_generator import WorldGenerator
from game.systems.day_night_cycle import DayNightCycle
from game.systems.fade_in_system import FadeInSystem
from game.components.fade_in import FadeInEffect
from game.ai.ai_generator import AIContentGenerator
from aurora_engine.database.db_manager import DatabaseManager
from aurora_engine.database.schema import DatabaseSchema
from game.utils.chunk_worker import generate_chunk_meshes
from game.utils.terrain import get_height_at_world_pos
from aurora_engine.physics.collider import HeightfieldCollider, MeshCollider, BoxCollider, Collider
from aurora_engine.physics.rigidbody import RigidBody, StaticBody
from aurora_engine.core.logging import get_logger

import numpy as np
import json
import os
import time
import random
from typing import Dict, Tuple, Set
from concurrent.futures import ThreadPoolExecutor

logger = get_logger()

class Rifted(Application):
    """
    The Main RPG Game Application.
    """

    def initialize_game(self):
        """Game-specific initialization."""
        logger.info("Initializing Rifted Game...")
        # Initialize Database (MySQL)
        db_config = self.config.get('database', {})
        if not db_config:
             db_config = {
                'host': 'localhost',
                'user': 'root',
                'password': '',
                'database': 'rifted_db',
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

        # Create player entity
        self.player = self.world.create_entity()
        player_transform = self.player.add_component(Transform())
        # Initial position will be adjusted after terrain load
        player_transform.set_world_position(np.array([0, 0, 10.0], dtype=np.float32))

        # Add player visual (Capsule)
        player_mesh = create_capsule_mesh(radius=0.5, height=2.0)
        self.player.add_component(MeshRenderer(mesh=player_mesh, color=(0.2, 0.4, 0.8, 1.0)))
        
        # Add player physics
        self.player.add_component(Collider(BoxCollider(np.array([1.0, 1.0, 2.0], dtype=np.float32))))
        rb = self.player.add_component(RigidBody())
        rb.mass = 80.0 # Standard human mass
        rb.use_gravity = True
        rb.lock_rotation = True # Prevent rolling

        # Add player-specific components
        from game.components.player import PlayerController
        self.player.add_component(PlayerController())

        # Setup camera to follow player
        from aurora_engine.camera.camera import Camera
        from aurora_engine.camera.third_person import ThirdPersonController

        camera = Camera()
        # Pass input manager to controller
        self.camera_controller = ThirdPersonController(camera, player_transform, self.input)
        # Inject physics world for collision
        self.camera_controller.physics_world = self.physics

        self.renderer.register_camera(camera)
        
        # Lock mouse for camera control
        self.input.set_mouse_lock(True)

        # Add game systems
        player_system = PlayerSystem(self.input)
        # Inject camera transform into player system for camera-relative movement
        player_system.camera_transform = camera.transform
        self.world.add_system(player_system)
        
        self.world.add_system(FadeInSystem())
        
        # Pass player transform to DayNightCycle for shadow following
        day_night = DayNightCycle(self.renderer)
        day_night.target = player_transform
        self.world.add_system(day_night)
        
        dialogue_system = DialogueSystem(self.ui)
        dialogue_system.ai_generator = self.ai_generator
        self.world.add_system(dialogue_system)

        # Chunk Management
        self.loaded_chunks: Dict[Tuple[int, int], list] = {} 
        self.pending_data: Dict[Tuple[int, int], object] = {} 
        self.pending_meshes: Dict[Tuple[int, int], object] = {} 

        self.load_radius = 4 
        self.unload_radius = 6
        self.last_chunk_check = 0.0
        
        # Store current dimension ID
        self.current_dimension_id = None

        # Load Game World
        self._load_game_world()
        
        # Setup Sun/Moon Visuals
        self._setup_celestial_bodies()

    def _setup_celestial_bodies(self):
        """Create visual entities for Sun and Moon."""
        # Sun
        sun = self.world.create_entity()
        sun.add_component(Transform())
        sun.add_component(MeshRenderer(mesh=create_cube_mesh(10.0), color=(1.0, 1.0, 0.8, 1.0))) # Placeholder sphere
        
        # Moon
        moon = self.world.create_entity()
        moon.add_component(Transform())
        moon.add_component(MeshRenderer(mesh=create_cube_mesh(8.0), color=(0.8, 0.8, 1.0, 1.0)))
        
        # Pass entities to DayNightCycle system
        # We need to find the system first
        for system in self.world.systems:
            if isinstance(system, DayNightCycle):
                system.sun_entity = sun
                system.moon_entity = moon
                break

    def update(self, dt: float, alpha: float):
        """Override update to update chunk management."""
        super().update(dt, alpha)
        
        # Chunk Management
        self.last_chunk_check += dt
        if self.last_chunk_check > 0.5:
            self._manage_chunks()
            self.last_chunk_check = 0.0
        
        self._process_futures()
        
        # Toggle mouse lock with Escape
        if self.input.is_key_down('escape'):
            self.input.set_mouse_lock(False)
        elif self.input.is_key_down('mouse1') and not self.input.mouse_locked:
            self.input.set_mouse_lock(True)
        
    def late_update(self, dt: float, alpha: float):
        """Update camera after physics."""
        if hasattr(self, 'camera_controller'):
            self.camera_controller.update(dt, alpha)

    def _process_futures(self):
        """Process completed futures."""
        # 4. Process Stage 1 Futures (Data Gen)
        completed_data = []
        for coords, future in self.pending_data.items():
            if future.done():
                try:
                    region_data = future.result()
                    mesh_future = self.mesh_executor.submit(generate_chunk_meshes, region_data)
                    self.pending_meshes[coords] = mesh_future
                except Exception as e:
                    logger.error(f"Chunk data generation failed for {coords}: {e}")
                completed_data.append(coords)
                
        for coords in completed_data:
            del self.pending_data[coords]
                
        # 5. Process Stage 2 Futures (Mesh Gen)
        completed_meshes = []
        for coords, future in self.pending_meshes.items():
            if future.done():
                try:
                    meshes = future.result()
                    region_data = self.world_generator.generate_region(self.current_dimension_id, coords[0], coords[1])
                    self._instantiate_chunk(region_data, meshes, fade_in=True)
                except Exception as e:
                    logger.error(f"Chunk mesh generation failed for {coords}: {e}")
                completed_meshes.append(coords)
                
        for coords in completed_meshes:
            del self.pending_meshes[coords]

    def _manage_chunks(self):
        """Handle loading and unloading of chunks."""
        # Use player position for chunk loading
        player_pos = self.player.get_component(Transform).get_world_position()
        
        # 1. Determine needed chunks
        all_needed = self.world_generator.get_chunks_in_radius(player_pos[0], player_pos[1], self.load_radius)
        
        # Sort by distance to player
        all_needed.sort(key=lambda c: (c[0]*100 - player_pos[0])**2 + (c[1]*100 - player_pos[1])**2)
        needed_chunks = set(all_needed)
        
        # 2. Unload distant chunks
        chunks_to_unload = []
        for coords in self.loaded_chunks:
            chunk_world_x = coords[0] * 100.0
            chunk_world_y = coords[1] * 100.0
            dist = np.sqrt((chunk_world_x - player_pos[0])**2 + (chunk_world_y - player_pos[1])**2)
            
            if dist > self.unload_radius * 100.0:
                chunks_to_unload.append(coords)
                
        for coords in chunks_to_unload:
            self._unload_chunk(coords)
            
        # 3. Load new chunks
        max_concurrent_loads = 8
        current_loads = len(self.pending_data) + len(self.pending_meshes)
        
        for coords in needed_chunks:
            if current_loads >= max_concurrent_loads:
                break
                
            if coords not in self.loaded_chunks and coords not in self.pending_data and coords not in self.pending_meshes:
                self._request_chunk_load(coords)
                current_loads += 1
        
        self._process_futures()

    def _request_chunk_load(self, coords: Tuple[int, int]):
        """Start async generation."""
        future = self.world_generator.generate_region_async(self.current_dimension_id, coords[0], coords[1])
        self.pending_data[coords] = future

    def _unload_chunk(self, coords: Tuple[int, int]):
        """Destroy entities in a chunk."""
        if coords in self.loaded_chunks:
            entities = self.loaded_chunks[coords]
            for entity in entities:
                self.world.destroy_entity(entity)
            del self.loaded_chunks[coords]

    def _load_game_world(self):
        """Load the main game world."""
        # Use a random seed for the main world
        seed = random.randint(0, 2**32 - 1)
        # Use a unique dimension ID each time to force new generation
        self.current_dimension_id = f"dim_main_{seed}"
        dim = self.world_generator.get_or_create_dimension(self.current_dimension_id, seed)
        logger.info(f"Entered Dimension: {dim['name']} (Seed: {seed})")
        
        # Initial Load (Synchronous)
        logger.info("Loading initial area...")
        regions = self.world_generator.load_chunks_around_player(self.current_dimension_id, 0, 0, radius=self.load_radius)
        
        for region in regions:
            meshes = generate_chunk_meshes(region)
            self._instantiate_chunk(region, meshes, fade_in=False)
            
        # Adjust Player Height
        center_region = next((r for r in regions if r['coordinates_x'] == 0 and r['coordinates_y'] == 0), None)
        if center_region:
            h = get_height_at_world_pos(0, 0, center_region, cell_size=100.0/20.0) # 20 is resolution
            self.player.get_component(Transform).set_world_position(np.array([0, 0, h + 5.0], dtype=np.float32)) # Drop from 5m

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
            # Check if model_path is present (for buildings)
            if 'model_path' in entity_data:
                e.add_component(MeshRenderer(model_path=entity_data['model_path']))
            else:
                e.add_component(MeshRenderer(mesh=mesh, color=(1.0, 1.0, 1.0, 1.0)))
                
            if fade_in: e.add_component(FadeInEffect(duration=1.5))
            
            # Colliders
            if entity_data['type'] == 'prop':
                if entity_data['model'] == 'rock':
                    e.add_component(Collider(MeshCollider(mesh, convex=True)))
                elif entity_data['model'] == 'tree':
                    scale = entity_data.get('scale', 1.0)
                    e.add_component(Collider(BoxCollider(np.array([0.5 * scale, 0.5 * scale, 4.0 * scale], dtype=np.float32))))
            elif entity_data['type'] == 'structure':
                e.add_component(Collider(BoxCollider(np.array([4.0, 3.0, 3.0], dtype=np.float32))))
            
            # Add StaticBody for props/structures
            e.add_component(StaticBody())
            
            chunk_entities.append(e)
                
        # Terrain
        if meshes['terrain']:
            ground = self.world.create_entity()
            gt = ground.add_component(Transform())
            
            rx = region_data['coordinates_x'] * 100.0
            ry = region_data['coordinates_y'] * 100.0
            gt.set_world_position(np.array([rx, ry, 0], dtype=np.float32))
            
            ground.add_component(MeshRenderer(mesh=meshes['terrain'], color=(1.0, 1.0, 1.0, 1.0)))
            if fade_in: ground.add_component(FadeInEffect(duration=1.5))
            
            # Add StaticBody and MeshCollider for terrain
            ground.add_component(StaticBody())
            ground.add_component(Collider(MeshCollider(meshes['terrain'], convex=False)))
            
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
        if fade_in: water.add_component(FadeInEffect(duration=1.5))
        
        # Add StaticBody for water
        water.add_component(StaticBody())
        
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
            'title': 'Rifted',
        },
        'database': {
            'host': 'localhost',
            'user': 'root',
            'password': 'CeneX_1234', # Set your MySQL password here
            'database': 'rifted_db',
            'port': 3306
        }
    }

    # Write config to file so Application loads it correctly
    with open("config.json", "w") as f:
        json.dump(config_data, f, indent=2)

    game = Rifted("config.json")
    game.run()
