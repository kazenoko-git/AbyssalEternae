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
        
        angle = self.time * 2 * math.pi
        radius = 100.0
        
        sun_x = -math.sin(angle) * radius
        sun_z = math.cos(angle) * radius
        sun_y = 0 
        
        if self.sun_entity:
            t = self.sun_entity.get_component(Transform)
            t.set_world_position(np.array([sun_x, sun_y, sun_z], dtype=np.float32))
            
        self.sun_light_node.setPos(sun_x, sun_y, sun_z)
        self.sun_light_node.lookAt(0, 0, 0)
        
        moon_x = -sun_x
        moon_z = -sun_z
        moon_y = -sun_y
        
        if self.moon_entity:
            t = self.moon_entity.get_component(Transform)
            t.set_world_position(np.array([moon_x, moon_y, moon_z], dtype=np.float32))
            
        self.moon_light_node.setPos(moon_x, moon_y, moon_z)
        self.moon_light_node.lookAt(0, 0, 0)
        
        self._update_colors(sun_z)

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
        self.renderer.backend.base.setBackgroundColor(sky_color)
        self.fog.setColor(sky_color)
        self.sun_light_node.node().setColor(sun_color)
        self.moon_light_node.node().setColor(moon_color)
        self.ambient_light_node.node().setColor(ambient)
