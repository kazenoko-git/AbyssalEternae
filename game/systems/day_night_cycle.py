# game/systems/day_night_cycle.py

from aurora_engine.ecs.system import System
from aurora_engine.scene.transform import Transform
from aurora_engine.rendering.mesh import MeshRenderer, create_sphere_mesh
from aurora_engine.rendering.light import DirectionalLight, AmbientLight
import numpy as np
import math
from aurora_engine.core.logging import get_logger

logger = get_logger()

class DayNightCycle(System):
    """
    Manages the day/night cycle, including sun/moon movement and lighting/sky color changes.
    """

    def __init__(self, renderer, day_duration: float = 60.0):
        super().__init__()
        self.renderer = renderer
        self.day_duration = day_duration # Seconds for a full day
        self.time = 0.0 # 0.0 to 1.0 (0=Noon, 0.5=Midnight)
        self.paused = False
        
        self.sun_entity = None
        self.moon_entity = None
        self.ambient_entity = None
        
        self.target = None # Player transform to follow
        self.orbit_radius = 500.0 # Distance from player
        
        self._setup_lights()
        self._setup_color_gradient()
        
        # Start at evening to show transition
        self.time = 0.3 
        # logger.debug("DayNightCycle initialized")

    def _setup_lights(self):
        pass

    def _setup_color_gradient(self):
        # Time -> Color mapping
        self.sky_colors = {
            0.0: (0.53, 0.8, 0.92), # Noon
            0.20: (0.9, 0.6, 0.3),  # Sunset
            0.30: (0.1, 0.1, 0.3),  # Twilight
            0.5: (0.0, 0.0, 0.0),   # Midnight (Pitch Black for testing)
            0.70: (0.1, 0.1, 0.3),  # Twilight
            0.80: (0.9, 0.6, 0.3),  # Sunrise
            1.0: (0.53, 0.8, 0.92)  # Noon
        }
        self.sun_colors = {
            0.0: (1.0, 1.0, 0.9),
            0.20: (1.0, 0.8, 0.6),
            0.30: (0.0, 0.0, 0.0), # Fade to black
            0.5: (0.0, 0.0, 0.0),
            0.70: (0.0, 0.0, 0.0),
            0.80: (1.0, 0.8, 0.6),
            1.0: (1.0, 1.0, 0.9)
        }
        self.moon_colors = {
            0.0: (0.0, 0.0, 0.0),
            0.20: (0.0, 0.0, 0.0),
            0.30: (0.05, 0.05, 0.1), # Fade in (Dim)
            0.5: (0.1, 0.1, 0.15),   # Full moon light (Dim)
            0.70: (0.05, 0.05, 0.1),
            0.80: (0.0, 0.0, 0.0),
            1.0: (0.0, 0.0, 0.0)
        }
        self.ambient_colors = {
            0.0: (0.4, 0.4, 0.4),
            0.20: (0.3, 0.2, 0.2),
            0.30: (0.1, 0.1, 0.15),
            0.5: (0.01, 0.01, 0.02), # Almost pitch black ambient
            0.70: (0.1, 0.1, 0.15),
            0.80: (0.3, 0.2, 0.2),
            1.0: (0.4, 0.4, 0.4)
        }

    def get_required_components(self):
        return [] # Global system

    def update(self, entities, dt):
        if not self.paused:
            self.time = (self.time + dt / self.day_duration) % 1.0
        
        # Calculate Sun/Moon Position relative to Player
        center_pos = np.array([0, 0, 0], dtype=np.float32)
        if self.target:
            center_pos = self.target.get_world_position()
            
        angle = self.time * 2 * math.pi

        sun_h = math.cos(angle) * self.orbit_radius # Height (+Z)
        sun_w = -math.sin(angle) * self.orbit_radius # East/West (-X)

        sun_pos = np.array([
            center_pos[0] + sun_w,
            center_pos[1],
            center_pos[2] + sun_h
        ], dtype=np.float32)
        
        moon_pos = np.array([
            center_pos[0] - sun_w,
            center_pos[1],
            center_pos[2] - sun_h
        ], dtype=np.float32)
        
        # Update Entities
        if self.sun_entity:
            t = self.sun_entity.get_component(Transform)
            t.set_world_position(sun_pos)
            self._look_at(t, center_pos)
            
        if self.moon_entity:
            t = self.moon_entity.get_component(Transform)
            t.set_world_position(moon_pos)
            self._look_at(t, center_pos)
            
        self._update_colors(sun_h)

    def _look_at(self, transform, target_pos):
        origin = transform.get_world_position()
        direction = target_pos - origin
        if np.linalg.norm(direction) < 0.001: return
        direction /= np.linalg.norm(direction)
        
        up = np.array([0, 0, 1], dtype=np.float32)
        right = np.cross(direction, up)
        if np.linalg.norm(right) < 0.001:
            right = np.array([1, 0, 0], dtype=np.float32)
        else:
            right /= np.linalg.norm(right)
        up = np.cross(right, direction)
        up /= np.linalg.norm(up)
        
        rot_mat = np.eye(3, dtype=np.float32)
        rot_mat[:, 0] = right
        rot_mat[:, 1] = direction # Forward
        rot_mat[:, 2] = up
        
        from aurora_engine.utils.math import matrix_to_quaternion
        transform.local_rotation = matrix_to_quaternion(rot_mat)

    def _interpolate_color(self, gradient, time):
        keys = sorted(gradient.keys())
        key1 = keys[0]
        key2 = keys[-1]
        for k in keys:
            if k <= time:
                key1 = k
            if k >= time:
                key2 = k
                break
        if key1 == key2:
            return np.array(gradient[key1], dtype=np.float32)
            
        t = (time - key1) / (key2 - key1)
        c1 = np.array(gradient[key1], dtype=np.float32)
        c2 = np.array(gradient[key2], dtype=np.float32)
        return c1 * (1 - t) + c2 * t

    def _update_colors(self, sun_height):
        sky_color = self._interpolate_color(self.sky_colors, self.time)
        sun_color = self._interpolate_color(self.sun_colors, self.time)
        moon_color = self._interpolate_color(self.moon_colors, self.time)
        ambient_color = self._interpolate_color(self.ambient_colors, self.time)
        
        # Apply colors
        if hasattr(self.renderer.backend, 'base'):
            self.renderer.backend.base.setBackgroundColor(sky_color[0], sky_color[1], sky_color[2], 1)
        
        # Update Fog
        if hasattr(self.renderer.backend.scene_graph, 'getFog'):
            fog = self.renderer.backend.scene_graph.getFog()
            if fog:
                fog.setColor(sky_color[0], sky_color[1], sky_color[2])
            
        # Update Light Components
        if self.sun_entity:
            light = self.sun_entity.get_component(DirectionalLight)
            if light:
                light.color = sun_color

        if self.moon_entity:
            light = self.moon_entity.get_component(DirectionalLight)
            if light:
                light.color = moon_color

        if self.ambient_entity:
            light = self.ambient_entity.get_component(AmbientLight)
            if light:
                light.color = ambient_color
