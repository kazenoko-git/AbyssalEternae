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
    Minimal test for Basic Shadow Shader.
    """

    def initialize_game(self):
        logger.info("Initializing Basic Lighting Test...")
        
        # 1. Setup Camera
        self.camera = Camera()
        self.camera.transform.set_world_position(np.array([0, -40, 30], dtype=np.float32))
        q_cam = quaternion_from_euler(np.radians(np.array([-35.0, 0.0, 0.0], dtype=np.float32)))
        self.camera.transform.set_world_rotation(q_cam)
        
        self.renderer.register_camera(self.camera)
        
        # Free fly controller
        self.cam_controller = FreeFlyController(self.camera)
        self.cam_controller.move_speed = 10.0
        
        # 2. Load Shaders
        self._load_shaders()
        
        # 3. Create Scene
        self._create_scene()
        
        # 4. Create Lights
        self._create_lights()
        
        # 5. Apply Shaders to Scene
        self._start_shader_update_task()

        self._v_key_pressed = False
        
        logger.info("Lighting Test Initialized.")
        logger.info("Controls: WASD to Move, Hold Right Click + Mouse to Look.")
        logger.info("Debug: 'V' to toggle Shadow Map View, 'L' to rotate Sun.")

    def _load_shaders(self):
        """Load the basic diagnostic shader."""
        shader_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../shaders"))
        
        # Toon Shader (Characters)
        toon_vert_path = os.path.join(shader_dir, "toon.vert")
        toon_frag_path = os.path.join(shader_dir, "toon.frag")
        
        # World Shader (Terrain/Environment)
        world_vert_path = os.path.join(shader_dir, "world.vert")
        world_frag_path = os.path.join(shader_dir, "world.frag")
        
        # Outline Shader
        out_vert_path = os.path.join(shader_dir, "outline.vert")
        out_frag_path = os.path.join(shader_dir, "outline.frag")
        
        if not os.path.exists(toon_vert_path) or not os.path.exists(toon_frag_path):
            logger.error("Toon shader files not found!")
            self.toon_shader = None
        else:
            try:
                self.toon_shader = PandaShader.load(
                    PandaShader.SL_GLSL,
                    vertex=toon_vert_path,
                    fragment=toon_frag_path
                )
                logger.info("Toon shader loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load toon shader: {e}")
                self.toon_shader = None

        if not os.path.exists(world_vert_path) or not os.path.exists(world_frag_path):
            logger.error("World shader files not found!")
            self.world_shader = None
        else:
            try:
                self.world_shader = PandaShader.load(
                    PandaShader.SL_GLSL,
                    vertex=world_vert_path,
                    fragment=world_frag_path
                )
                logger.info("World shader loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load world shader: {e}")
                self.world_shader = None

        if not os.path.exists(out_vert_path) or not os.path.exists(out_frag_path):
            logger.error("Outline shader files not found!")
            self.outline_shader = None
        else:
            try:
                self.outline_shader = PandaShader.load(
                    PandaShader.SL_GLSL,
                    vertex=out_vert_path,
                    fragment=out_frag_path
                )
                logger.info("Outline shader loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load outline shader: {e}")
                self.outline_shader = None

    def _create_scene(self):
        self.scene_entities = []
        
        # Ground Plane (World Shader)
        ground = self.world.create_entity()
        ground.add_component(Transform())
        ground.get_component(Transform).set_world_position(np.array([0, 0, 0], dtype=np.float32))
        ground.get_component(Transform).set_local_scale(np.array([100, 100, 1], dtype=np.float32))
        ground.add_component(MeshRenderer(mesh=create_plane_mesh(), color=(0.8, 0.8, 0.8, 1.0)))
        ground.tag = "world" # Tag for shader selection
        self.scene_entities.append(ground)
        
        # Center Sphere (Toon Shader)
        sphere = self.world.create_entity()
        sphere.add_component(Transform())
        sphere.get_component(Transform).set_world_position(np.array([0, 0, 2], dtype=np.float32))
        sphere.get_component(Transform).set_local_scale(np.array([2, 2, 2], dtype=np.float32))
        sphere.add_component(MeshRenderer(mesh=create_sphere_mesh(), color=(1.0, 0.2, 0.2, 1.0)))
        sphere.tag = "character"
        self.scene_entities.append(sphere)
        
        # Offset Cube (Toon Shader)
        cube = self.world.create_entity()
        cube.add_component(Transform())
        cube.get_component(Transform).set_world_position(np.array([5, 2, 1.5], dtype=np.float32))
        q_cube = quaternion_from_euler(np.radians(np.array([45.0, 45.0, 0.0], dtype=np.float32)))
        cube.get_component(Transform).set_world_rotation(q_cube)
        cube.get_component(Transform).set_local_scale(np.array([1.5, 1.5, 1.5], dtype=np.float32))
        cube.add_component(MeshRenderer(mesh=create_cube_mesh(), color=(0.2, 1.0, 0.2, 1.0)))
        cube.tag = "character"
        self.scene_entities.append(cube)
        
        # Tall Pillar (World Shader)
        pillar = self.world.create_entity()
        pillar.add_component(Transform())
        pillar.get_component(Transform).set_world_position(np.array([-5, 2, 4], dtype=np.float32))
        pillar.get_component(Transform).set_local_scale(np.array([1, 1, 8.0], dtype=np.float32))
        pillar.add_component(MeshRenderer(mesh=create_cube_mesh(), color=(0.2, 0.2, 1.0, 1.0)))
        pillar.tag = "world"
        self.scene_entities.append(pillar)

    def _create_lights(self):
        # Ambient Light
        self.amb_entity = self.world.create_entity()
        amb_comp = AmbientLight(color=(0.3, 0.3, 0.4), intensity=0.4)
        self.amb_entity.add_component(amb_comp)
        
        # Create Panda3D Ambient Light
        p_alight = PandaAmbientLight("ambient")
        p_alight.setColor(Vec4(0.3, 0.3, 0.4, 1.0) * 0.4)
        amb_np = self.renderer.backend.base.render.attachNewNode(p_alight)
        self.renderer.backend.base.render.setLight(amb_np)
        
        # Directional Light (Sun)
        self.sun = self.world.create_entity()
        self.sun.add_component(Transform())
        self.sun.get_component(Transform).set_world_position(np.array([0, -40, 40], dtype=np.float32))
        
        # Initial Rotation
        self.sun_pitch = -60.0
        self.sun_yaw = 0.0
        self._update_sun_rotation()
        
        dlight = DirectionalLight(color=(1.0, 0.95, 0.8), intensity=2.0)
        dlight.cast_shadows = True
        dlight.shadow_map_size = 4096 
        dlight.shadow_film_size = 100.0 
        self.sun.add_component(dlight)
        
        # Create Panda3D Directional Light
        p_dlight = PandaDirectionalLight("sun")
        p_dlight.setColor(Vec4(1.0, 0.95, 0.8, 1.0) * 2.0)
        
        # Configure Shadows
        p_dlight.setShadowCaster(True, 4096, 4096)
        lens = p_dlight.getLens()
        lens.setFilmSize(100, 100)
        lens.setNearFar(10, 1000)
        
        # Store in component and attach
        dlight._backend_handle = self.renderer.backend.base.render.attachNewNode(p_dlight)
        self.renderer.backend.base.render.setLight(dlight._backend_handle)
        
        # Debug Sun
        sun_viz = self.world.create_entity()
        sun_viz.add_component(Transform())
        sun_viz.get_component(Transform).set_world_position(np.array([0, -40, 40], dtype=np.float32))
        sun_viz.get_component(Transform).set_local_scale(np.array([2, 2, 2], dtype=np.float32))
        sun_viz.add_component(MeshRenderer(mesh=create_sphere_mesh(), color=(1.0, 1.0, 0.0, 1.0)))
        self.scene_entities.append(sun_viz)

    def _update_sun_rotation(self):
        q_sun = quaternion_from_euler(np.radians(np.array([self.sun_pitch, self.sun_yaw, 0.0], dtype=np.float32)))
        self.sun.get_component(Transform).set_world_rotation(q_sun)

    def _start_shader_update_task(self):
        if not self.toon_shader and not self.world_shader:
            return
        # Run every frame to update uniforms (light direction, camera pos)
        self.renderer.backend.base.taskMgr.add(self._update_shader_task, "UpdateShaderTask")

    def _update_shader_task(self, task):
        # Calculate Global Uniforms
        cam_pos = self.camera.transform.get_world_position()
        
        # Calculate Light Direction (Vector TO Light)
        # Sun forward is the direction rays travel. Vector TO sun is opposite.
        sun_transform = self.sun.get_component(Transform)
        rot = sun_transform.get_world_rotation()
        p3d_quat = Quat(rot[3], rot[0], rot[1], rot[2])
        sun_fwd = p3d_quat.getForward()
        light_dir = -sun_fwd 
        
        # Ambient Color
        ambient_color = Vec3(0.2, 0.2, 0.2)
        if hasattr(self, 'amb_entity'):
            amb_comp = self.amb_entity.get_component(AmbientLight)
            if amb_comp:
                c = amb_comp.color * amb_comp.intensity
                ambient_color = Vec3(c[0], c[1], c[2])

        for entity in self.scene_entities:
            mesh_renderer = entity.get_component(MeshRenderer)
            if mesh_renderer and hasattr(mesh_renderer, '_node_path') and mesh_renderer._node_path:
                np = mesh_renderer._node_path
                
                # Determine Shader based on Tag
                target_shader = self.world_shader
                is_character = False
                
                if hasattr(entity, 'tag') and entity.tag == "character":
                    target_shader = self.toon_shader
                    is_character = True
                
                if target_shader:
                    np.setShader(target_shader)
                    
                    np.setShaderInput("u_light_dir", Vec3(light_dir[0], light_dir[1], light_dir[2]))
                    np.setShaderInput("u_view_pos", Vec3(cam_pos[0], cam_pos[1], cam_pos[2]))
                    np.setShaderInput("u_ambient_color", ambient_color)
                    
                    if hasattr(mesh_renderer, 'color'):
                        np.setShaderInput("u_color", Vec4(*mesh_renderer.color))
                
                # Fix Visibility: Cull Back faces to hide insides
                np.setDepthWrite(True)
                np.setDepthTest(True)
                np.setAttrib(CullFaceAttrib.make(CullFaceAttrib.M_cull_clockwise))
                
                # 2. Handle Outline (Inverted Hull) - Only for Characters
                if is_character and self.outline_shader:
                    # Check if outline node exists to avoid creating it every frame
                    outline_node = np.find("outline_shell")
                    if outline_node.is_empty():
                        # Create outline node by copying the geometry
                        outline_node = np.copy_to(np)
                        outline_node.set_name("outline_shell")
                        
                        # Reset transform so it doesn't double-apply the parent's scale/pos
                        outline_node.set_transform(TransformState.make_identity())
                        
                        # Apply Outline Shader
                        outline_node.set_shader(self.outline_shader)
                        
                        # Cull FRONT faces so we see the inside of the expanded hull
                        outline_node.set_attrib(CullFaceAttrib.make(CullFaceAttrib.M_cull_counter_clockwise))
                        
                        # Render outline BEFORE the main object to avoid Z-fighting
                        outline_node.set_bin("background", 10)
                        outline_node.set_depth_write(True)
                        outline_node.set_depth_test(True)
                    
                    # Update Outline Uniforms
                    outline_node.set_shader_input("outline_width", 0.03) # Thin outline
                    outline_node.set_shader_input("outline_color", Vec4(0.0, 0.0, 0.0, 1.0)) # Black
                
        return task.cont

    def update(self, dt: float, alpha: float):
        super().update(dt, alpha)
        
        # Update Camera
        if hasattr(self, 'cam_controller'):
            move = np.zeros(3)
            if self.input.is_key_down('w'): move[1] += 1
            if self.input.is_key_down('s'): move[1] -= 1
            if self.input.is_key_down('a'): move[0] -= 1
            if self.input.is_key_down('d'): move[0] += 1
            if self.input.is_key_down('q'): move[2] += 1
            if self.input.is_key_down('e'): move[2] -= 1
            
            self.cam_controller.move(move)
            
            md = self.input.get_mouse_delta()
            if self.input.is_key_down('mouse3') or self.input.mouse_locked:
                self.cam_controller.rotate(md[0] * -50, md[1] * 50)
                
            self.cam_controller.update(dt)

        # Toggle Shadow Map Debug
        if self.input.is_key_down('v'):
            if not self._v_key_pressed:
                self.renderer.backend.base.bufferViewer.toggleEnable()
                self.renderer.backend.base.bufferViewer.setPosition("llcorner")
                self.renderer.backend.base.bufferViewer.setLayout("vline")
                self._v_key_pressed = True
        else:
            self._v_key_pressed = False

        # Rotate Sun
        if self.input.is_key_down('l'):
            t = self.time.get_time()
            self.sun_yaw += dt * 20.0
            self._update_sun_rotation()
            
            # Force update the Panda Node from the component transform
            if hasattr(self, 'sun'):
                transform = self.sun.get_component(Transform)
                dlight_component = self.sun.get_component(DirectionalLight)
                if dlight_component and dlight_component._backend_handle:
                    light_np = dlight_component._backend_handle
                    pos = transform.get_world_position()
                    rot = transform.get_world_rotation()
                    light_np.setPos(pos[0], pos[1], pos[2])
                    light_np.setQuat(Quat(rot[3], rot[0], rot[1], rot[2]))

        # Toggle mouse lock
        if self.input.is_key_down('escape'):
            self.input.set_mouse_lock(False)
        elif self.input.is_key_down('mouse1'):
            self.input.set_mouse_lock(True)

if __name__ == "__main__":
    config_path = "lighting_test_config.json"
    with open(config_path, "w") as f:
        json.dump({
            'rendering': {
                'width': 1280, 
                'height': 720, 
                'title': 'Basic Lighting Test'
            }, 
            'database': {'database': 'test.db'}
        }, f)

    app = LightingTest(config_path)
    try:
        app.run()
    finally:
        if os.path.exists(config_path):
            os.remove(config_path)
