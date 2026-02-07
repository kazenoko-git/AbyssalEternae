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
        self.camera.transform.set_world_position(np.array([0, -40, 30], dtype=np.float32))
        q_cam = quaternion_from_euler(np.radians(np.array([-35.0, 0.0, 0.0], dtype=np.float32)))
        self.camera.transform.set_world_rotation(q_cam)
        
        self.renderer.register_camera(self.camera)
        
        self.cam_controller = FreeFlyController(self.camera)
        self.cam_controller.move_speed = 10.0
        
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
        
        ground = self.world.create_entity()
        ground.add_component(Transform(
            position=np.array([0, 0, 0], dtype=np.float32),
            scale=np.array([100, 100, 1], dtype=np.float32)
        ))
        ground.add_component(MeshRenderer(mesh=create_plane_mesh(), color=(0.8, 0.8, 0.8, 1.0)))
        ground.tag = "world"
        self.scene_entities.append(ground)
        
        sphere = self.world.create_entity()
        sphere.add_component(Transform(
            position=np.array([0, 0, 2], dtype=np.float32),
            scale=np.array([2, 2, 2], dtype=np.float32)
        ))
        sphere.add_component(MeshRenderer(mesh=create_sphere_mesh(), color=(1.0, 0.2, 0.2, 1.0)))
        sphere.tag = "character"
        self.scene_entities.append(sphere)
        
        cube = self.world.create_entity()
        cube.add_component(Transform(
            position=np.array([5, 2, 1.5], dtype=np.float32),
            rotation=quaternion_from_euler(np.radians(np.array([45.0, 45.0, 0.0], dtype=np.float32))),
            scale=np.array([1.5, 1.5, 1.5], dtype=np.float32)
        ))
        cube.add_component(MeshRenderer(mesh=create_cube_mesh(), color=(0.2, 1.0, 0.2, 1.0)))
        cube.tag = "character"
        self.scene_entities.append(cube)
        
        # Make the blue pillar a character too so it gets an outline, as per user feedback
        pillar = self.world.create_entity()
        pillar.add_component(Transform(
            position=np.array([-5, 2, 4], dtype=np.float32),
            scale=np.array([1, 1, 8.0], dtype=np.float32)
        ))
        pillar.add_component(MeshRenderer(mesh=create_cube_mesh(), color=(0.2, 0.2, 1.0, 1.0)))
        pillar.tag = "character"
        self.scene_entities.append(pillar)

    def _create_lights(self):
        """Creates lights via the ECS to be managed by the LightSystem."""
        # Ambient Light
        ambient_entity = self.world.create_entity()
        ambient_entity.add_component(AmbientLight(color=(0.2, 0.25, 0.3), intensity=0.5))

        # Directional Light (Sun)
        self.sun_entity = self.world.create_entity()
        self.sun_entity.add_component(Transform()) # The LightSystem will use this transform
        self.sun_entity.add_component(DirectionalLight(
            color=(1.0, 0.95, 0.8),
            intensity=1.5,
            cast_shadows=True,
            shadow_map_size=4096,
            shadow_film_size=120.0
        ))
        
        # Initial sun position and rotation
        self.sun_yaw = 45.0
        sun_transform = self.sun_entity.get_component(Transform)
        sun_transform.set_world_position(np.array([0, -80, 60], dtype=np.float32))
        self._update_sun_rotation()


    def _update_sun_rotation(self):
        """Rotates the sun's transform component."""
        if hasattr(self, 'sun_entity'):
            q_sun = quaternion_from_euler(np.radians(np.array([-60.0, self.sun_yaw, 0.0], dtype=np.float32)))
            self.sun_entity.get_component(Transform).set_world_rotation(q_sun)

    def _setup_render_states(self):
        """Applies global render states. Lights are handled by the LightSystem."""
        render = self.renderer.backend.base.render
        render.setShaderAuto()
        render.setShaderInput("receive_shadows", True)

    def _apply_shaders_task(self, task):
        """
        Task that waits for Panda3D nodes to be created from ECS components,
        then applies the correct shader to them.
        """
        for entity in self.scene_entities:
            if hasattr(entity, '_shader_applied') and entity._shader_applied:
                continue

            mesh_renderer = entity.get_component(MeshRenderer)
            if mesh_renderer and mesh_renderer._node_path:
                logger.info(f"Applying shader to entity with tag: {entity.tag}")
                np = mesh_renderer._node_path
                target_shader = None
                is_character = False

                if hasattr(entity, 'tag'):
                    if entity.tag == "character":
                        target_shader = self.toon_shader
                        is_character = True
                    elif entity.tag == "world":
                        target_shader = self.world_shader

                if target_shader:
                    np.setShader(target_shader, 1)
                
                np.setAttrib(CullFaceAttrib.make(CullFaceAttrib.M_cull_clockwise))
                np.setShaderInput("u_color", Vec4(*mesh_renderer.color))

                if is_character and self.outline_shader:
                    outline_node = np.copy_to(np.getParent())
                    outline_node.setName(f"{np.getName()}-outline")
                    outline_node.setTransform(np.getTransform())
                    
                    outline_node.setShader(self.outline_shader)
                    outline_node.setAttrib(CullFaceAttrib.make(CullFaceAttrib.M_cull_counter_clockwise))
                    outline_node.set_bin("background", 10)
                    
                    # Correct Z-fighting fix: Use offset and keep depth writing enabled.
                    outline_node.setAttrib(DepthOffsetAttrib.make(5))
                    outline_node.setDepthWrite(True) 

                    outline_node.setShaderInput("outline_width", 0.03)
                    outline_node.setShaderInput("outline_color", Vec4(0.0, 0.0, 0.0, 1.0))

                entity._shader_applied = True
        
        all_done = all(hasattr(e, '_shader_applied') for e in self.scene_entities if e.has_component(MeshRenderer))
        if all_done and self.scene_entities:
            logger.info("All shaders applied. Stopping shader application task.")
            return task.done

        return task.cont

    def update(self, dt: float, alpha: float):
        super().update(dt, alpha)
        
        # Update Camera
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

        # Toggle Shadow Map Debug
        if self.input.is_key_down('v'):
            if not self._v_key_pressed:
                is_enabled = self.renderer.backend.base.bufferViewer.isEnabled()
                self.renderer.backend.base.bufferViewer.enable(not is_enabled)
                if not is_enabled:
                    self.renderer.backend.base.bufferViewer.setPosition("llcorner")
                    self.renderer.backend.base.bufferViewer.setLayout("vline")
                self._v_key_pressed = True
        else:
            self._v_key_pressed = False

        # Rotate Sun
        if self.input.is_key_down('l'):
            self.sun_yaw += dt * 45.0
            self._update_sun_rotation()

        # Toggle mouse lock
        if self.input.is_key_down('escape'):
            self.input.set_mouse_lock(False)
        elif self.input.is_key_down('mouse1'):
            self.input.set_mouse_lock(True)

if __name__ == "__main__":
    config_path = os.path.join(os.path.dirname(__file__), "test_config.json")
    with open(config_path, "w") as f:
        json.dump({
            'rendering': {'width': 1280, 'height': 720, 'title': 'Hybrid Lighting & Shading Test'}, 
            'database': {'database': 'test.db'}
        }, f)

    app = LightingTest(config_path)
    try:
        app.run()
    finally:
        if os.path.exists(config_path):
            os.remove(config_path)


