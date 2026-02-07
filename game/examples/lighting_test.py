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
from aurora_engine.rendering.light import DirectionalLight, AmbientLight
from aurora_engine.camera.camera import Camera
from aurora_engine.camera.free_fly import FreeFlyController
from aurora_engine.core.logging import get_logger
from aurora_engine.utils.math import quaternion_from_euler
from panda3d.core import Shader as PandaShader, loadPrcFileData, Vec4, Quat, Vec3, CullFaceAttrib, TransformState, DepthOffsetAttrib
from panda3d.core import DirectionalLight as PandaDirectionalLight, AmbientLight as PandaAmbientLight

logger = get_logger()

# --- Configuration for Shadow Map Debugging ---
# Set to 1 to see the shadow map buffer
loadPrcFileData("", "show-buffers 0") 

class LightingTest(Application):
    """
    Demonstrates a hybrid rendering pipeline with two distinct shading models:
    1. World/Terrain: Stylized Half-Lambert lighting.
    2. Characters: Toon/Cel shading with outlines.
    Both shaders use the same global lighting and shadow map, managed by the engine's ECS.
    """

    def initialize_game(self):
        logger.info("Initializing Hybrid Lighting Test...")
        
        # 1. Setup Camera
        self.camera = Camera()
        self.camera.transform.set_world_position(np.array([0, -40, 15], dtype=np.float32))
        q_cam = quaternion_from_euler(np.radians(np.array([-25.0, 0.0, 0.0], dtype=np.float32)))
        self.camera.transform.set_world_rotation(q_cam)
        
        self.renderer.register_camera(self.camera)
        
        self.cam_controller = FreeFlyController(self.camera)
        self.cam_controller.move_speed = 15.0
        
        # 2. Load Shaders
        self._load_shaders()
        
        # 3. Create Scene using the ECS
        self._create_scene()
        
        # 4. Create Lights using the ECS
        self._create_lights()
        
        # 5. Apply Global Render States
        self._setup_render_states()
        
        # 6. Start a task to apply shaders to newly created nodes
        self.renderer.backend.base.taskMgr.add(self._apply_shaders_task, "ApplyShadersTask")

        self._v_key_pressed = False
        
        logger.info("Lighting Test Initialized.")
        logger.info("Controls: WASD to Move, Hold Right Click + Mouse to Look.")
        logger.info("Debug: 'V' to toggle Shadow Map View, 'L' to rotate Sun.")

    def _load_shaders(self):
        shader_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../shaders"))
        self.toon_shader = self._load_single_shader("toon", shader_dir)
        self.world_shader = self._load_single_shader("world", shader_dir)
        self.outline_shader = self._load_single_shader("outline", shader_dir)

    def _load_single_shader(self, name, shader_dir):
        vert_path = os.path.join(shader_dir, f"{name}.vert")
        frag_path = os.path.join(shader_dir, f"{name}.frag")
        if not os.path.exists(vert_path) or not os.path.exists(frag_path):
            logger.error(f"{name.capitalize()} shader files not found!")
            return None
        try:
            shader = PandaShader.load(PandaShader.SL_GLSL, vertex=vert_path, fragment=frag_path)
            logger.info(f"{name.capitalize()} shader loaded successfully.")
            return shader
        except Exception as e:
            logger.error(f"Failed to load {name} shader: {e}")
            return None

    def _create_scene(self):
        """Creates the scene geometry using the engine's ECS."""
        self.scene_entities = []

        # Ground
        ground = self.world.create_entity()
        ground_transform = Transform()
        ground_transform.set_local_position(np.array([0, 0, -0.5], dtype=np.float32))
        ground_transform.set_local_scale(np.array([100, 100, 1], dtype=np.float32))
        ground.add_component(ground_transform)
        ground.add_component(MeshRenderer(mesh=create_plane_mesh(), color=(0.5, 0.7, 0.4, 1.0)))
        ground.tag = "world"
        self.scene_entities.append(ground)

        # Red Sphere (Character)
        sphere = self.world.create_entity()
        sphere_transform = Transform()
        sphere_transform.set_local_position(np.array([0, 0, 2], dtype=np.float32))
        sphere_transform.set_local_scale(np.array([2, 2, 2], dtype=np.float32))
        sphere.add_component(sphere_transform)
        sphere.add_component(MeshRenderer(mesh=create_sphere_mesh(), color=(1.0, 0.2, 0.2, 1.0)))
        sphere.tag = "character"
        self.scene_entities.append(sphere)

        # Green Cube (Character)
        cube = self.world.create_entity()
        cube_transform = Transform()
        cube_transform.set_local_position(np.array([8, 5, 1.5], dtype=np.float32))
        cube_transform.set_local_rotation(quaternion_from_euler(np.radians(np.array([0.0, 0.0, 35.0], dtype=np.float32))))
        cube_transform.set_local_scale(np.array([3, 3, 3], dtype=np.float32))
        cube.add_component(cube_transform)
        cube.add_component(MeshRenderer(mesh=create_cube_mesh(), color=(0.2, 1.0, 0.2, 1.0)))
        cube.tag = "character"
        self.scene_entities.append(cube)

        # Blue Pillar (Character)
        pillar = self.world.create_entity()
        pillar_transform = Transform()
        pillar_transform.set_local_position(np.array([-8, 5, 4], dtype=np.float32))
        pillar_transform.set_local_scale(np.array([1, 1, 8.0], dtype=np.float32))
        pillar.add_component(pillar_transform)
        pillar.add_component(MeshRenderer(mesh=create_cube_mesh(), color=(0.2, 0.2, 1.0, 1.0)))
        pillar.tag = "character"
        self.scene_entities.append(pillar)

    def _create_lights(self):
        """Creates lights via the ECS to be managed by the LightSystem."""
        # Ambient Light
        self.ambient_light_entity = self.world.create_entity()
        self.ambient_light_entity.add_component(AmbientLight(color=(0.2, 0.25, 0.35), intensity=0.4))

        # Directional Light (Sun)
        self.sun_entity = self.world.create_entity()
        self.sun_entity.add_component(Transform()) 
        dlight_comp = DirectionalLight(
            color=(1.0, 0.95, 0.85),
            intensity=1.5
        )
        dlight_comp.cast_shadows = True
        dlight_comp.shadow_map_size = 4096
        dlight_comp.shadow_film_size = 100.0 # Tighter film size for better resolution
        self.sun_entity.add_component(dlight_comp)
        
        # Initial sun rotation
        self.sun_yaw = 135.0 
        self._update_sun_rotation()

    def _update_sun_rotation(self):
        """Rotates the sun's transform component."""
        if hasattr(self, 'sun_entity'):
            # A pitch of -45 to -60 degrees gives good shadow angles
            q_sun = quaternion_from_euler(np.radians(np.array([-50.0, self.sun_yaw, 0.0], dtype=np.float32)))
            self.sun_entity.get_component(Transform).set_world_rotation(q_sun)

    def _setup_render_states(self):
        """Applies global render states. The shader is responsible for using lights."""
        # We don't call setShaderAuto because we are setting shaders manually.
        # We will pass the lights to the shaders as inputs.
        self.renderer.backend.base.render.setShaderInput("receive_shadows", True)

    def _apply_shaders_task(self, task):
        """
        Waits for ECS components to create Panda3D nodes, then applies shaders and light inputs.
        """
        # Find the light node paths once the LightSystem has created them
        dlight_comp = self.sun_entity.get_component(DirectionalLight)
        alight_comp = self.ambient_light_entity.get_component(AmbientLight)

        if not (dlight_comp and dlight_comp._backend_handle and alight_comp and alight_comp._backend_handle):
            return task.cont # Wait for lights to be initialized by the system

        dlight_np = dlight_comp._backend_handle
        alight_np = alight_comp._backend_handle

        for entity in self.scene_entities:
            if hasattr(entity, '_shader_applied') and entity._shader_applied:
                continue

            mesh_renderer = entity.get_component(MeshRenderer)
            if mesh_renderer and mesh_renderer._node_path:
                np = mesh_renderer._node_path
                target_shader = None
                is_character = False

                if entity.tag == "character":
                    target_shader = self.toon_shader
                    is_character = True
                elif entity.tag == "world":
                    target_shader = self.world_shader

                if target_shader:
                    # Set the shader and the light inputs
                    np.setShader(target_shader, 1)
                    np.setShaderInput("u_ambient_light", alight_np)
                    np.setShaderInput("u_directional_light", dlight_np)
                
                np.setAttrib(CullFaceAttrib.make(CullFaceAttrib.M_cull_clockwise))
                np.setShaderInput("u_color", Vec4(*mesh_renderer.color))

                if is_character and self.outline_shader:
                    outline_node = np.copy_to(np.getParent())
                    outline_node.setName(f"{np.getName()}-outline")
                    outline_node.setTransform(np.getTransform())
                    
                    outline_node.setShader(self.outline_shader)
                    outline_node.setAttrib(CullFaceAttrib.make(CullFaceAttrib.M_cull_counter_clockwise))
                    outline_node.set_bin("background", 10)
                    
                    outline_node.setAttrib(DepthOffsetAttrib.make(5))
                    outline_node.setDepthWrite(True) 
                    outline_node.setShaderInput("outline_width", 0.04)
                    outline_node.setShaderInput("outline_color", Vec4(0.0, 0.0, 0.0, 1.0))

                entity._shader_applied = True
        
        all_done = all(hasattr(e, '_shader_applied') for e in self.scene_entities if e.has_component(MeshRenderer))
        if all_done and self.scene_entities:
            logger.info("All shaders and lights applied. Stopping task.")
            return task.done

        return task.cont

    def update(self, dt: float, alpha: float):
        super().update(dt, alpha)
        
        # --- Input & Camera ---
        move = np.zeros(3)
        if self.input.is_key_down('w'): move[1] += 1
        if self.input.is_key_down('s'): move[1] -= 1
        if self.input.is_key_down('a'): move[0] -= 1
        if self.input.is_key_down('d'): move[0] += 1
        self.cam_controller.move(move)
        
        md = self.input.get_mouse_delta()
        if self.input.is_key_down('mouse3') or self.input.mouse_locked:
            self.cam_controller.rotate(md[0] * -50, md[1] * 50)
        self.cam_controller.update(dt)

        # --- Debug Controls ---
        # Toggle Shadow Map Debug
        if self.input.is_key_down('v') and not self._v_key_pressed:
            is_enabled = not self.renderer.backend.base.bufferViewer.isEnabled()
            self.renderer.backend.base.bufferViewer.enable(is_enabled)
            if is_enabled:
                self.renderer.backend.base.bufferViewer.setPosition("lrcorner")
                self.renderer.backend.base.bufferViewer.setLayout("vline")
            self._v_key_pressed = True
        elif not self.input.is_key_down('v'):
            self._v_key_pressed = False

        # Rotate Sun
        if self.input.is_key_down('l'):
            self.sun_yaw += dt * 90.0 # Faster rotation
            self._update_sun_rotation()

        # Toggle mouse lock
        if self.input.is_key_down('escape'):
            self.input.set_mouse_lock(False)
        elif self.input.is_key_down('mouse1'):
            self.input.set_mouse_lock(True)

if __name__ == "__main__":
    config_path = os.path.join(os.path.dirname(__file__), "test_config.json")
    # Clean up old config if it exists
    if os.path.exists(config_path):
        os.remove(config_path)
        
    with open(config_path, "w") as f:
        json.dump({
            'rendering': {'width': 1600, 'height': 900, 'title': 'Hybrid Lighting & Shading Test'}, 
            'database': {'database': 'test.db'}
        }, f, indent=4)

    app = LightingTest(config_path)
    try:
        app.run()
    finally:
        # Clean up config file to keep the directory clean
        if os.path.exists(config_path):
            pass # Keep it for inspection if needed, or os.remove(config_path)

