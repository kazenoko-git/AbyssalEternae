# game_project/main.py

from aurora_engine.core.application import Application
from aurora_engine.ecs.entity import Entity
from aurora_engine.scene.transform import Transform
from aurora_engine.rendering.mesh import MeshRenderer, create_cube_mesh, create_plane_mesh, create_capsule_mesh
from game.systems.player_system import PlayerSystem
from game.systems.player_action_system import PlayerActionSystem
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
from aurora_engine.ui.image import ImageWidget
from aurora_engine.ui.widget import Label

import numpy as np
import json
import os
import time
import random
import math
from typing import Dict, Tuple, Set
from concurrent.futures import ThreadPoolExecutor

logger = get_logger()

class AbyssalEternae(Application):
    """
    The Main RPG Game Application.
    """

    def initialize_game(self):
        """Game-specific initialization."""
        logger.info("Initializing Abyssal Eternae Game...")
        # Initialize Database (MySQL)
        db_config = self.config.get('database', {})
        if not db_config:
             db_config = {
                'host': 'localhost',
                'user': 'root',
                'password': '',
                'database': 'abyssal_eternae_db',
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

        # Add player visual
        # Using FBX as it is more reliable with current loader setup (auto-scaled and textured)
        self.player.add_component(MeshRenderer(model_path="assets/characters/maleMC.glb"))
        
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

        self.main_camera = Camera()
        # Pass input manager to controller
        self.camera_controller = ThirdPersonController(self.main_camera, player_transform, self.input)
        # Inject physics world for collision
        self.camera_controller.physics_world = self.physics

        self.renderer.register_camera(self.main_camera)
        
        # Lock mouse for camera control
        self.input.set_mouse_lock(True)

        # Add game systems
        player_system = PlayerSystem(self.input)
        # Inject camera transform into player system for camera-relative movement
        player_system.camera_transform = self.main_camera.transform
        self.world.add_system(player_system)
        
        # Add Player Action System
        self.world.add_system(PlayerActionSystem(self.input))
        
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

        # Render Radius Configuration
        self.chunk_size = 100.0
        self.render_radius_chunks = 4 # Reduced to 4 as requested
        self.render_radius_world = self.render_radius_chunks * self.chunk_size
        
        # Compatibility alias for load_radius
        self.load_radius = self.render_radius_chunks
        
        # Fog Radius (Must be smaller than render radius by at least 1 chunk)
        self.fog_radius = (self.render_radius_chunks - 1) * self.chunk_size
        
        self.last_chunk_check = 0.0
        
        # Store current dimension ID
        self.current_dimension_id = None
        
        # Debug State
        self.debug_panda_visible = False
        self.debug_overlay_visible = True
        self.debug_node_path = None
        
        # Secondary Camera Debug
        self.secondary_window = None
        self.secondary_camera = None
        self.debug_camera_active = False
        self.debug_cam_angle = 0.0
        self.debug_cam_distance = 150.0
        self.debug_cam_height = 100.0
        
        # Input Debounce
        self.f3_pressed = False
        self.f4_pressed = False
        self.f5_pressed = False
        self.c_pressed = False

        # Load Game World
        self._load_game_world()
        
        # Setup Sun/Moon Visuals
        self._setup_celestial_bodies()
        
        # Setup UI
        self._setup_ui()
        
        # Setup Fog
        self._setup_fog()

    def _setup_fog(self):
        """Setup distance fog for performance and atmosphere."""
        from panda3d.core import Fog
        fog = Fog("DistanceFog")
        fog.setColor(0.53, 0.8, 0.92) # Sky blue
        
        # Exponential fog density based on radius
        # Visibility ~ 3 / density
        # density = 3 / fog_radius
        # Reduced density significantly as requested ("fog is way too high")
        # Old: 3.0 / self.fog_radius
        # New: 1.0 / self.fog_radius (3x less dense)
        density = 1.0 / self.fog_radius
        fog.setExpDensity(density) 
        
        if hasattr(self.renderer.backend, 'scene_graph'):
            self.renderer.backend.scene_graph.setFog(fog)

    def _setup_ui(self):
        """Initialize basic game UI."""
        # Crosshair
        crosshair = ImageWidget("Crosshair", "assets/ui/crosshair.png")
        crosshair.size = np.array([32, 32], dtype=np.float32)
        # Center of screen
        w = self.config.get('rendering.width', 1280)
        h = self.config.get('rendering.height', 720)
        crosshair.position = np.array([w/2 - 16, h/2 - 16], dtype=np.float32)
        self.ui.add_widget(crosshair, layer='overlay')
        
        # Health Bar (Background)
        hp_bg = ImageWidget("HP_BG", "assets/ui/bar_bg.png")
        hp_bg.size = np.array([300, 30], dtype=np.float32)
        hp_bg.position = np.array([50, h - 50], dtype=np.float32)
        hp_bg.color = (0.2, 0.2, 0.2, 0.8)
        self.ui.add_widget(hp_bg, layer='hud')
        
        # Health Bar (Fill)
        hp_fill = ImageWidget("HP_Fill", "assets/ui/bar_fill.png")
        hp_fill.size = np.array([300, 30], dtype=np.float32)
        hp_fill.position = np.array([50, h - 50], dtype=np.float32)
        hp_fill.color = (0.8, 0.2, 0.2, 1.0)
        self.ui.add_widget(hp_fill, layer='hud')
        
        # Minimap Frame
        minimap = ImageWidget("Minimap", "assets/ui/minimap_frame.png")
        minimap.size = np.array([200, 200], dtype=np.float32)
        minimap.position = np.array([w - 220, 20], dtype=np.float32)
        self.ui.add_widget(minimap, layer='hud')
        
        # Debug Info
        self.debug_label = Label("DebugInfo", "FPS: 60")
        self.debug_label.position = np.array([10, 10], dtype=np.float32)
        self.ui.add_widget(self.debug_label, layer='overlay')

    def _setup_celestial_bodies(self):
        """Create visual entities for Sun and Moon."""
        # Sun (Billboard Plane)
        sun = self.world.create_entity()
        sun.add_component(Transform())
        
        # Use texture path for image
        sun_renderer = MeshRenderer(
            mesh=create_plane_mesh(100.0, 100.0), 
            color=(1.0, 1.0, 0.8, 1.0),
            texture_path="assets/textures/sun.png" # Placeholder path
        )
        sun_renderer.billboard = True # Always face camera
        sun.add_component(sun_renderer)
        
        # Moon (Billboard Plane)
        moon = self.world.create_entity()
        moon.add_component(Transform())
        
        moon_renderer = MeshRenderer(
            mesh=create_plane_mesh(80.0, 80.0), 
            color=(0.8, 0.8, 1.0, 1.0),
            texture_path="assets/textures/moon.png" # Placeholder path
        )
        moon_renderer.billboard = True # Always face camera
        moon.add_component(moon_renderer)
        
        # Pass entities to DayNightCycle system
        # We need to find the system first
        for system in self.world.systems:
            if isinstance(system, DayNightCycle):
                system.sun_entity = sun
                system.moon_entity = moon
                # Adjust distance in system if needed, or just rely on system updating position
                # Sun/Moon should be within fog radius so they are visible?
                # No, celestial bodies usually ignore fog or are rendered last.
                # But if we put them inside fog radius, they will be visible.
                # Let's put them at fog_radius - 50
                system.orbit_radius = self.fog_radius - 50.0 
                break

    def update(self, dt: float, alpha: float):
        """Override update to update chunk management."""
        super().update(dt, alpha)
        
        # Chunk Management
        self.last_chunk_check += dt
        if self.last_chunk_check > 0.5: # Check every 0.5s
            self._manage_chunks()
            self.last_chunk_check = 0.0
        
        self._process_futures()
        
        # Toggle mouse lock with Escape
        if self.input.is_key_down('escape'):
            self.input.set_mouse_lock(False)
        elif self.input.is_key_down('mouse1') and not self.input.mouse_locked:
            self.input.set_mouse_lock(True)
            
        # Debug Toggles (Proper Debounce)
        if self.input.is_key_down('f3'):
            if not self.f3_pressed:
                self.f3_pressed = True
                self.debug_panda_visible = not self.debug_panda_visible
                if hasattr(self.renderer.backend, 'base'):
                    self.renderer.backend.base.setFrameRateMeter(self.debug_panda_visible)
                    
                    # Toggle wireframe and physics debug
                    if self.debug_panda_visible:
                        self.renderer.backend.base.render.setRenderModeWireframe()
                        # Attach physics debug node
                        if not self.debug_node_path:
                            self.debug_node_path = self.physics.attach_debug_node(self.renderer.backend.scene_graph)
                        if self.debug_node_path:
                            self.debug_node_path.show()
                    else:
                        self.renderer.backend.base.render.clearRenderMode()
                        if self.debug_node_path:
                            self.debug_node_path.hide()
        else:
            self.f3_pressed = False
            
        # Secondary Camera Toggle (F3 + F4)
        if self.input.is_key_down('f3') and self.input.is_key_down('f4'):
            if not self.debug_camera_active:
                self.debug_camera_active = True
                self._open_secondary_window()
        
        # Update Debug Info
        if hasattr(self, 'debug_label') and self.debug_label.visible:
            fps = 1.0 / dt if dt > 0 else 60.0
            pos = self.player.get_component(Transform).get_world_position()
            self.debug_label.text = f"FPS: {fps:.0f} | Pos: {pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}"
        
    def late_update(self, dt: float, alpha: float):
        """Update camera after physics."""
        if hasattr(self, 'camera_controller'):
            self.camera_controller.update(dt, alpha)
            
        # Update secondary camera
        if self.secondary_window:
            # Manual Orbit Logic
            self.debug_cam_angle += dt * 0.2 # Slow rotation
            
            player_pos = self.player.get_component(Transform).get_world_position()
            
            # Calculate position
            x = player_pos[0] + math.cos(self.debug_cam_angle) * self.debug_cam_distance
            y = player_pos[1] + math.sin(self.debug_cam_angle) * self.debug_cam_distance
            z = player_pos[2] + self.debug_cam_height
            
            # Sync to Panda Node
            if hasattr(self, 'secondary_cam_np'):
                self.secondary_cam_np.setPos(x, y, z)
                self.secondary_cam_np.lookAt(player_pos[0], player_pos[1], player_pos[2])

    def _open_secondary_window(self):
        """Open a secondary window for debug rendering."""
        if self.secondary_window:
            return
            
        from panda3d.core import WindowProperties, Camera as PandaCamera, DisplayRegion, NodePath
        from aurora_engine.camera.camera import Camera
        
        base = self.renderer.backend.base
        
        # Open new window
        props = WindowProperties()
        props.setTitle("Debug View - Global Observer")
        props.setSize(640, 480)
        
        self.secondary_window = base.openWindow(props=props, makeCamera=False)
        
        # Create a new camera node for this window
        cam_node = PandaCamera('secondary_cam')
        # Set lens for wider view
        lens = cam_node.getLens()
        lens.setFov(90)
        lens.setNear(1.0)
        lens.setFar(5000.0) # Far clip to see everything
        
        self.secondary_cam_np = base.render.attachNewNode(cam_node)
        
        # Create display region
        dr = self.secondary_window.makeDisplayRegion()
        dr.setCamera(self.secondary_cam_np)
        
        # Create Engine Camera wrapper
        self.secondary_camera = Camera()
        
        logger.info("Secondary debug window opened")

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
        
        # Current Chunk Coordinates
        current_chunk_x = int(player_pos[0] / self.chunk_size)
        current_chunk_y = int(player_pos[1] / self.chunk_size)
        
        # 1. Determine needed chunks (Circular Radius + FOV Culling)
        needed_chunks = set()
        radius = self.render_radius_chunks
        
        # Get Camera Forward Vector for FOV culling
        cam_transform = self.main_camera.transform
        cam_fwd = cam_transform.forward
        cam_pos = cam_transform.get_world_position()
        
        # Iterate bounding box of circle
        for x in range(current_chunk_x - radius, current_chunk_x + radius + 1):
            for y in range(current_chunk_y - radius, current_chunk_y + radius + 1):
                # Chunk center position
                chunk_center_x = x * self.chunk_size + self.chunk_size / 2
                chunk_center_y = y * self.chunk_size + self.chunk_size / 2
                
                # Vector to chunk
                to_chunk = np.array([chunk_center_x - cam_pos[0], chunk_center_y - cam_pos[1], 0.0], dtype=np.float32)
                dist_sq = to_chunk[0]**2 + to_chunk[1]**2
                
                # Check circular distance
                if dist_sq <= (radius * self.chunk_size)**2:
                    # FOV Check (Dot Product)
                    # Normalize to_chunk
                    dist = np.sqrt(dist_sq)
                    if dist > 0.1: # Skip current chunk (always render)
                        to_chunk /= dist
                        # Project cam_fwd to 2D
                        cam_fwd_2d = np.array([cam_fwd[0], cam_fwd[1], 0.0], dtype=np.float32)
                        if np.linalg.norm(cam_fwd_2d) > 0.01:
                            cam_fwd_2d /= np.linalg.norm(cam_fwd_2d)
                            
                            dot = np.dot(to_chunk, cam_fwd_2d)
                            
                            # FOV Culling Logic:
                            # dot < -0.5 means strictly behind (outside 240 degree cone)
                            # BUT we want to keep 1-2 chunks behind the player rendered.
                            
                            # Calculate distance in chunks
                            chunk_dist = dist / self.chunk_size
                            
                            # If chunk is very close (within 1-2 chunks), keep it regardless of FOV
                            # This satisfies "Make one-two chunks behind the player render as well"
                            if chunk_dist <= 1.5: # Keep immediate surroundings
                                pass
                            elif dot < -0.5: # Otherwise apply culling
                                continue
                    
                    needed_chunks.add((x, y))
        
        # 2. Update Visibility (Don't Unload, just Hide)
        # We iterate ALL loaded chunks.
        # If in needed_chunks -> Ensure Visible
        # If NOT in needed_chunks -> Ensure Hidden (but keep in memory)
        
        # Note: We still need to load new chunks if they are needed but not loaded.
        
        for coords, entities in self.loaded_chunks.items():
            # If debug mode is active, render ALL loaded chunks
            # FIX: Only force visibility if debug camera is active, otherwise respect needed_chunks
            # The previous logic was: should_be_visible = coords in needed_chunks or self.debug_camera_active
            # This meant if debug camera was active, EVERYTHING loaded was visible.
            # But the user said "Using f3+f4 debug makes it so that ALL chunks render. Fix that."
            # This implies they want to see the CULLING in action from the debug view.
            
            # Correct Logic:
            # We want to see exactly what the main camera sees (culled state) even in debug view.
            # The debug camera is just an observer. It shouldn't change the game state.
            should_be_visible = coords in needed_chunks
            
            for entity in entities:
                # Toggle MeshRenderer visibility
                mesh_renderer = entity.get_component(MeshRenderer)
                if mesh_renderer:
                    mesh_renderer.visible = should_be_visible
                    # Force update backend node immediately
                    if hasattr(mesh_renderer, '_node_path') and mesh_renderer._node_path:
                        if should_be_visible:
                            mesh_renderer._node_path.show()
                        else:
                            mesh_renderer._node_path.hide()
                            
        # 3. Load new chunks
        # Only load if not already in loaded_chunks
        max_concurrent_loads = 8
        current_loads = len(self.pending_data) + len(self.pending_meshes)
        
        # Sort needed chunks by distance to player so closest load first
        sorted_needed = sorted(list(needed_chunks), key=lambda c: (c[0]*self.chunk_size - player_pos[0])**2 + (c[1]*self.chunk_size - player_pos[1])**2)
        
        for coords in sorted_needed:
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
        
        # Load initial chunks synchronously to prevent falling through floor
        player_pos = self.player.get_component(Transform).get_world_position()
        current_chunk_x = int(player_pos[0] / self.chunk_size)
        current_chunk_y = int(player_pos[1] / self.chunk_size)
        
        radius = self.render_radius_chunks
        for x in range(current_chunk_x - radius, current_chunk_x + radius + 1):
            for y in range(current_chunk_y - radius, current_chunk_y + radius + 1):
                if (x - current_chunk_x)**2 + (y - current_chunk_y)**2 <= radius**2:
                    region = self.world_generator.generate_region(self.current_dimension_id, x, y)
                    meshes = generate_chunk_meshes(region)
                    self._instantiate_chunk(region, meshes, fade_in=False)
            
        # Adjust Player Height
        center_region = self.world_generator.generate_region(self.current_dimension_id, 0, 0)
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
                
            if fade_in: e.add_component(FadeInEffect(duration=0.5))
            
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
            if fade_in: ground.add_component(FadeInEffect(duration=0.5))
            
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
        if fade_in: water.add_component(FadeInEffect(duration=0.5))
        
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
            'title': 'Abyssal Eternae',
        },
        'database': {
            'host': 'localhost',
            'user': 'root',
            'password': 'Yippee_12345', # Set your MySQL password here
            'database': 'abyssal_eternae_db',
            'port': 3306
        }
    }

    # Write config to file so Application loads it correctly
    with open("config.json", "w") as f:
        json.dump(config_data, f, indent=2)

    game = AbyssalEternae("config.json")
    game.run()
