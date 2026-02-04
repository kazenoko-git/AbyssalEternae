# game/examples/lighting_test.py

import sys
import os
import numpy as np
import math
import json

# Add project root to path if running directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from aurora_engine.core.application import Application
from aurora_engine.scene.transform import Transform
from aurora_engine.rendering.mesh import MeshRenderer, create_cube_mesh, create_sphere_mesh, create_plane_mesh
from aurora_engine.rendering.light import DirectionalLight, AmbientLight, PointLight
from aurora_engine.camera.camera import Camera
from aurora_engine.camera.free_fly import FreeFlyController
from aurora_engine.core.logging import get_logger
from aurora_engine.utils.math import quaternion_from_euler, quaternion_from_axis_angle

logger = get_logger()

class LightingTest(Application):
    """
    Standalone test for lighting and shadows.
    """

    def initialize_game(self):
        logger.info("Initializing Lighting Test...")
        
        # 1. Setup Camera
        self.camera = Camera()
        self.camera.transform.set_world_position(np.array([0, -10, 5], dtype=np.float32))
        # Look at origin roughly (Pitch -20)
        # Initial rotation handled by controller update, but we can set initial pitch/yaw
        # self.camera.transform.set_world_rotation(...) 
        
        self.renderer.register_camera(self.camera)
        
        # Free fly controller
        self.cam_controller = FreeFlyController(self.camera)
        self.cam_controller.move_speed = 5.0
        
        # 2. Create Scene
        self._create_scene()
        
        # 3. Create Lights
        self._create_lights()
        
        logger.info("Lighting Test Initialized.")
        logger.info("Controls: WASD to Move, Hold Right Click + Mouse to Look.")

    def _create_scene(self):
        # Ground Plane
        ground = self.world.create_entity()
        ground.add_component(Transform())
        ground.get_component(Transform).set_world_position(np.array([0, 0, 0], dtype=np.float32))
        ground.get_component(Transform).set_local_scale(np.array([20, 20, 1], dtype=np.float32))
        ground.add_component(MeshRenderer(mesh=create_plane_mesh(), color=(0.8, 0.8, 0.8, 1.0))) # Light gray
        
        # Center Sphere
        sphere = self.world.create_entity()
        sphere.add_component(Transform())
        sphere.get_component(Transform).set_world_position(np.array([0, 0, 1], dtype=np.float32))
        sphere.add_component(MeshRenderer(mesh=create_sphere_mesh(), color=(1.0, 0.2, 0.2, 1.0))) # Red
        
        # Offset Cube
        cube = self.world.create_entity()
        cube.add_component(Transform())
        cube.get_component(Transform).set_world_position(np.array([3, 2, 1], dtype=np.float32))
        # Rotate cube to make shading obvious
        q_cube = quaternion_from_euler(np.radians(np.array([45.0, 45.0, 0.0], dtype=np.float32)))
        cube.get_component(Transform).set_world_rotation(q_cube)
        cube.add_component(MeshRenderer(mesh=create_cube_mesh(), color=(0.2, 1.0, 0.2, 1.0))) # Green
        
        # Tall Pillar (Cylinder-ish using scaled cube)
        pillar = self.world.create_entity()
        pillar.add_component(Transform())
        pillar.get_component(Transform).set_world_position(np.array([-3, 2, 2], dtype=np.float32))
        pillar.get_component(Transform).set_local_scale(np.array([0.5, 0.5, 4.0], dtype=np.float32))
        pillar.add_component(MeshRenderer(mesh=create_cube_mesh(), color=(0.2, 0.2, 1.0, 1.0))) # Blue

    def _create_lights(self):
        # Ambient Light (Base fill)
        amb = self.world.create_entity()
        amb.add_component(AmbientLight(color=(0.1, 0.1, 0.15), intensity=0.5))
        
        # Directional Light (Sun)
        self.sun = self.world.create_entity()
        self.sun.add_component(Transform())
        self.sun.get_component(Transform).set_world_position(np.array([0, -10, 10], dtype=np.float32))
        
        # Pointing down-forward
        q_sun = quaternion_from_euler(np.radians(np.array([-45.0, -20.0, 0.0], dtype=np.float32)))
        self.sun.get_component(Transform).set_world_rotation(q_sun)
        
        dlight = DirectionalLight(color=(1.0, 0.9, 0.8), intensity=2.0)
        dlight.cast_shadows = True
        dlight.shadow_map_size = 4096
        dlight.shadow_film_size = 30.0
        self.sun.add_component(dlight)
        
        # Point Light (Moving)
        self.point_light = self.world.create_entity()
        self.point_light.add_component(Transform())
        self.point_light.get_component(Transform).set_world_position(np.array([0, 5, 2], dtype=np.float32))
        
        plight = PointLight(color=(0.0, 1.0, 1.0), intensity=5.0, radius=10.0)
        plight.attenuation = (1.0, 0.1, 0.01)
        self.point_light.add_component(plight)
        
        # Visual marker for point light
        self.point_light.add_component(MeshRenderer(mesh=create_sphere_mesh(radius=0.2), color=(0.0, 1.0, 1.0, 1.0)))

    def update(self, dt: float, alpha: float):
        super().update(dt, alpha)
        
        # Update Camera
        if hasattr(self, 'cam_controller'):
            # Simple input handling for test
            move = np.zeros(3)
            if self.input.is_key_down('w'): move[1] += 1
            if self.input.is_key_down('s'): move[1] -= 1
            if self.input.is_key_down('a'): move[0] -= 1
            if self.input.is_key_down('d'): move[0] += 1
            if self.input.is_key_down('q'): move[2] += 1
            if self.input.is_key_down('e'): move[2] -= 1
            
            self.cam_controller.move(move)
            
            # Mouse look
            md = self.input.get_mouse_delta()
            if self.input.is_key_down('mouse3') or self.input.mouse_locked: # Right click or locked
                # Reduced sensitivity for smoother control
                self.cam_controller.rotate(md[0] * -50, md[1] * 50)
                
            self.cam_controller.update(dt)
            
        # Animate Point Light
        t = self.time.get_time()
        x = math.sin(t) * 5.0
        y = math.cos(t) * 5.0
        self.point_light.get_component(Transform).set_world_position(np.array([x, y, 2.0], dtype=np.float32))

        # Toggle mouse lock
        if self.input.is_key_down('escape'):
            self.input.set_mouse_lock(False)
        elif self.input.is_key_down('mouse1'):
            self.input.set_mouse_lock(True)

if __name__ == "__main__":
    config_path = "lighting_test_config.json"
    # Create temp config
    with open(config_path, "w") as f:
        json.dump({'rendering': {'width': 1280, 'height': 720, 'title': 'Lighting Test'}, 'database': {'database': 'test.db'}}, f)

    app = LightingTest(config_path)
    try:
        app.run()
    finally:
        if os.path.exists(config_path):
            os.remove(config_path)