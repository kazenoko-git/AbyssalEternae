# game/managers/debug_manager.py

import math
import numpy as np
from typing import Optional
from aurora_engine.core.logging import get_logger
from aurora_engine.input.input_manager import InputManager
from aurora_engine.rendering.renderer import Renderer
from aurora_engine.physics.physics_world import PhysicsWorld
from aurora_engine.ui.widget import Label
from aurora_engine.scene.transform import Transform

logger = get_logger()

class DebugManager:
    """
    Manages debug features like overlays, wireframe toggles, and secondary cameras.
    """
    
    def __init__(self, renderer: Renderer, input_manager: InputManager, physics_world: PhysicsWorld, ui_manager):
        self.renderer = renderer
        self.input = input_manager
        self.physics = physics_world
        self.ui = ui_manager
        
        # State
        self.debug_panda_visible = False
        self.debug_node_path = None
        self.f3_pressed = False
        self.f4_pressed = False
        
        # Secondary Camera
        self.secondary_window = None
        self.secondary_cam_np = None
        self.debug_camera_active = False
        self.debug_cam_angle = 0.0
        self.debug_cam_distance = 150.0
        self.debug_cam_height = 100.0
        
        # UI
        self.debug_label = Label("DebugInfo", "FPS: 60")
        self.debug_label.position = np.array([10, 10], dtype=np.float32)
        self.ui.add_widget(self.debug_label, layer='overlay')

    def update(self, dt: float, player_pos: np.ndarray):
        """Update debug logic."""
        self._handle_input()
        self._update_ui(dt, player_pos)
        
        if self.secondary_window:
            self._update_secondary_camera(dt, player_pos)

    def _handle_input(self):
        """Handle debug key toggles."""
        # F3: Toggle Wireframe / Physics Debug
        if self.input.is_key_down('f3'):
            if not self.f3_pressed:
                self.f3_pressed = True
                self._toggle_debug_view()
        else:
            self.f3_pressed = False
            
        # F3 + F4: Toggle Secondary Camera
        if self.input.is_key_down('f3') and self.input.is_key_down('f4'):
            if not self.debug_camera_active:
                self.debug_camera_active = True
                self._open_secondary_window()

    def _toggle_debug_view(self):
        """Toggle visual debug modes."""
        self.debug_panda_visible = not self.debug_panda_visible
        
        if hasattr(self.renderer.backend, 'base'):
            base = self.renderer.backend.base
            base.setFrameRateMeter(self.debug_panda_visible)
            
            if self.debug_panda_visible:
                base.render.setRenderModeWireframe()
                if not self.debug_node_path:
                    self.debug_node_path = self.physics.attach_debug_node(self.renderer.backend.scene_graph)
                if self.debug_node_path:
                    self.debug_node_path.show()
            else:
                base.render.clearRenderMode()
                if self.debug_node_path:
                    self.debug_node_path.hide()

    def _update_ui(self, dt: float, player_pos: np.ndarray):
        """Update debug overlay text."""
        if self.debug_label.visible:
            fps = 1.0 / dt if dt > 0 else 60.0
            self.debug_label.text = f"FPS: {fps:.0f} | Pos: {player_pos[0]:.1f}, {player_pos[1]:.1f}, {player_pos[2]:.1f}"

    def _open_secondary_window(self):
        """Open a secondary window for global observation."""
        if self.secondary_window:
            return
            
        from panda3d.core import WindowProperties, Camera as PandaCamera
        
        base = self.renderer.backend.base
        props = WindowProperties()
        props.setTitle("Debug View - Global Observer")
        props.setSize(640, 480)
        
        self.secondary_window = base.openWindow(props=props, makeCamera=False)
        cam_node = PandaCamera('secondary_cam')
        lens = cam_node.getLens()
        lens.setFov(90)
        lens.setNear(1.0)
        lens.setFar(5000.0)
        
        self.secondary_cam_np = base.render.attachNewNode(cam_node)
        dr = self.secondary_window.makeDisplayRegion()
        dr.setCamera(self.secondary_cam_np)
        
        logger.info("Secondary debug window opened")

    def _update_secondary_camera(self, dt: float, target_pos: np.ndarray):
        """Orbit secondary camera around target."""
        self.debug_cam_angle += dt * 0.2
        
        x = target_pos[0] + math.cos(self.debug_cam_angle) * self.debug_cam_distance
        y = target_pos[1] + math.sin(self.debug_cam_angle) * self.debug_cam_distance
        z = target_pos[2] + self.debug_cam_height
        
        if self.secondary_cam_np:
            self.secondary_cam_np.setPos(x, y, z)
            self.secondary_cam_np.lookAt(target_pos[0], target_pos[1], target_pos[2])
