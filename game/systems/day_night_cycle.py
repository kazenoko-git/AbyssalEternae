# game/systems/day_night_cycle.py

from aurora_engine.ecs.system import System
from aurora_engine.scene.transform import Transform
from aurora_engine.rendering.mesh import MeshRenderer, create_sphere_mesh
from panda3d.core import Vec4, DirectionalLight, AmbientLight, Fog
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
        
        self.sun_entity = None
        self.moon_entity = None
        self.sun_light_node = None
        self.moon_light_node = None
        self.ambient_light_node = None
        self.fog = None
        
        self.target = None # Player transform to follow
        self.orbit_radius = 500.0 # Distance from player
        
        self._setup_lights()
        self._setup_color_gradient()
        # logger.debug("DayNightCycle initialized")

    def _setup_lights(self):
        # Sun Light
        dlight = DirectionalLight('sun_light')
        dlight.setShadowCaster(True, 2048, 2048) # Enable Shadows
        # Adjust shadow lens to cover visible area
        lens = dlight.getLens()
        lens.setFilmSize(200, 200) # Cover 200x200 area around camera
        lens.setNearFar(10, 1000)
        
        self.sun_light_node = self.renderer.backend.scene_graph.attachNewNode(dlight)
        self.renderer.backend.scene_graph.setLight(self.sun_light_node)
        
        # Moon Light
        mlight = DirectionalLight('moon_light')
        mlight.setColor(Vec4(0.2, 0.2, 0.3, 1))
        mlight.setShadowCaster(True, 1024, 1024) # Enable Shadows (lower res for night)
        lens = mlight.getLens()
        lens.setFilmSize(200, 200)
        lens.setNearFar(10, 1000)

        self.moon_light_node = self.renderer.backend.scene_graph.attachNewNode(mlight)
        self.renderer.backend.scene_graph.setLight(self.moon_light_node)
        
        # Ambient Light
        alight = AmbientLight('ambient_light')
        self.ambient_light_node = self.renderer.backend.scene_graph.attachNewNode(alight)
        self.renderer.backend.scene_graph.setLight(self.ambient_light_node)
        
        # Fog
        self.fog = Fog("DayNightFog")
        self.fog.setExpDensity(0.002)
        self.renderer.backend.scene_graph.setFog(self.fog)

    def _setup_color_gradient(self):
        # Time -> Color mapping
        self.sky_colors = {
            0.0: Vec4(0.53, 0.8, 0.92, 1), # Noon
            0.20: Vec4(0.9, 0.6, 0.3, 1),  # Sunset
            0.30: Vec4(0.1, 0.1, 0.3, 1),  # Twilight
            0.5: Vec4(0.05, 0.05, 0.1, 1), # Midnight
            0.70: Vec4(0.1, 0.1, 0.3, 1),  # Twilight
            0.80: Vec4(0.9, 0.6, 0.3, 1),  # Sunrise
            1.0: Vec4(0.53, 0.8, 0.92, 1)  # Noon
        }
        self.sun_colors = {
            0.0: Vec4(1.0, 1.0, 0.9, 1),
            0.20: Vec4(1.0, 0.8, 0.6, 1),
            0.30: Vec4(0,0,0,1), # Fade to black
            0.5: Vec4(0,0,0,1),
            0.70: Vec4(0,0,0,1),
            0.80: Vec4(1.0, 0.8, 0.6, 1),
            1.0: Vec4(1.0, 1.0, 0.9, 1)
        }
        self.moon_colors = {
            0.0: Vec4(0,0,0,1),
            0.20: Vec4(0,0,0,1),
            0.30: Vec4(0.1, 0.1, 0.2, 1), # Fade in
            0.5: Vec4(0.2, 0.2, 0.3, 1),  # Full moon light
            0.70: Vec4(0.1, 0.1, 0.2, 1),
            0.80: Vec4(0,0,0,1),
            1.0: Vec4(0,0,0,1)
        }
        self.ambient_colors = {
            0.0: Vec4(0.4, 0.4, 0.4, 1),
            0.20: Vec4(0.4, 0.3, 0.3, 1),
            0.30: Vec4(0.2, 0.2, 0.3, 1),
            0.5: Vec4(0.1, 0.1, 0.2, 1),
            0.70: Vec4(0.2, 0.2, 0.3, 1),
            0.80: Vec4(0.4, 0.3, 0.3, 1),
            1.0: Vec4(0.4, 0.4, 0.4, 1)
        }

    def get_required_components(self):
        return [] # Global system

    def update(self, entities, dt):
        self.time = (self.time + dt / self.day_duration) % 1.0
        
        # Calculate Sun/Moon Position relative to Player
        # They should orbit around the player to simulate being "infinitely far away" but visible
        center_pos = np.array([0, 0, 0], dtype=np.float32)
        if self.target:
            center_pos = self.target.get_world_position()
            
        angle = self.time * 2 * math.pi
        
        # Orbit in YZ plane (East-West)
        # Noon (0.0) -> Sun High (+Z)
        # Sunset (0.25) -> Sun West (-X)
        # Midnight (0.5) -> Sun Low (-Z)
        
        # We want Sun to rise in East (+X) and set in West (-X)
        # Angle 0 = Noon (Top)
        # Angle PI/2 = Sunset (West, -X)
        # Angle PI = Midnight (Bottom)
        # Angle 3PI/2 = Sunrise (East, +X)
        
        # Correct math for East-West orbit:
        # X = sin(angle) * radius (0 at noon, 1 at sunset, 0 at midnight, -1 at sunrise) -> Wait, sunrise is East (+X)
        # Let's align:
        # Time 0.0 (Noon): Sun at (0, 0, +R)
        # Time 0.25 (Sunset): Sun at (-R, 0, 0) (West)
        # Time 0.75 (Sunrise): Sun at (+R, 0, 0) (East)
        
        sun_x = math.sin(angle) * self.orbit_radius # 0 -> 1 -> 0 -> -1
        # We want +1 at 0.75 (Sunrise) and -1 at 0.25 (Sunset)
        # sin(0.75 * 2pi) = sin(1.5pi) = -1. Wrong direction.
        # Let's use cos/sin standard circle and rotate.
        
        # Standard:
        # 0.0 -> Top (+Z)
        # 0.25 -> Right (+X)
        # 0.5 -> Bottom (-Z)
        # 0.75 -> Left (-X)
        
        # We want 0.25 to be West (-X). So invert X.
        
        sun_h = math.cos(angle) * self.orbit_radius # Height (+Z)
        sun_w = -math.sin(angle) * self.orbit_radius # East/West (-X)
        
        # Position relative to player
        # We keep Y constant relative to player so it follows them
        
        sun_pos = np.array([
            center_pos[0] + sun_w,
            center_pos[1], # Keep same Y depth
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
            # Look at player
            self._look_at(t, center_pos)
            
        if self.moon_entity:
            t = self.moon_entity.get_component(Transform)
            t.set_world_position(moon_pos)
            self._look_at(t, center_pos)
            
        # Update Lights
        # Directional light position doesn't matter for lighting, only rotation
        # But we set position for shadow mapping frustum center
        self.sun_light_node.setPos(sun_pos[0], sun_pos[1], sun_pos[2])
        self.sun_light_node.lookAt(center_pos[0], center_pos[1], center_pos[2])
        
        self.moon_light_node.setPos(moon_pos[0], moon_pos[1], moon_pos[2])
        self.moon_light_node.lookAt(center_pos[0], center_pos[1], center_pos[2])
        
        self._update_colors(sun_h)

    def _look_at(self, transform, target_pos):
        # Simple look at for entities
        # We need to set rotation quaternion
        # Vector from transform to target
        origin = transform.get_world_position()
        direction = target_pos - origin
        if np.linalg.norm(direction) < 0.001: return
        direction /= np.linalg.norm(direction)
        
        # Up vector (Global Z)
        up = np.array([0, 0, 1], dtype=np.float32)
        
        # Calculate Right
        right = np.cross(direction, up)
        if np.linalg.norm(right) < 0.001:
            right = np.array([1, 0, 0], dtype=np.float32)
        else:
            right /= np.linalg.norm(right)
            
        # Recalculate Up
        up = np.cross(right, direction)
        up /= np.linalg.norm(up)
        
        # Matrix
        rot_mat = np.eye(3, dtype=np.float32)
        rot_mat[:, 0] = right
        rot_mat[:, 1] = direction # Forward
        rot_mat[:, 2] = up
        
        from aurora_engine.utils.math import matrix_to_quaternion
        transform.local_rotation = matrix_to_quaternion(rot_mat)

    def _interpolate_color(self, gradient, time):
        keys = sorted(gradient.keys())
        
        # Find surrounding keys
        key1 = keys[0]
        key2 = keys[-1]
        for k in keys:
            if k <= time:
                key1 = k
            if k >= time:
                key2 = k
                break
                
        if key1 == key2:
            return gradient[key1]
            
        # Interpolate
        t = (time - key1) / (key2 - key1)
        return gradient[key1] * (1 - t) + gradient[key2] * t

    def _update_colors(self, sun_height):
        sky_color = self._interpolate_color(self.sky_colors, self.time)
        sun_color = self._interpolate_color(self.sun_colors, self.time)
        moon_color = self._interpolate_color(self.moon_colors, self.time)
        ambient = self._interpolate_color(self.ambient_colors, self.time)
        
        # Apply colors (no more switching lights on/off)
        if hasattr(self.renderer.backend, 'base'):
            self.renderer.backend.base.setBackgroundColor(sky_color)
        
        if self.fog:
            self.fog.setColor(sky_color)
            
        if self.sun_light_node:
            self.sun_light_node.node().setColor(sun_color)
            
        if self.moon_light_node:
            self.moon_light_node.node().setColor(moon_color)
            
        if self.ambient_light_node:
            self.ambient_light_node.node().setColor(ambient)
