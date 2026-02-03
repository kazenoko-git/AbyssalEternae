from aurora_engine.rendering.mesh import MeshRenderer, create_sphere_mesh
from aurora_engine.scene.transform import Transform
from aurora_engine.ecs.world import World
from aurora_engine.rendering.renderer import Renderer
from game.systems.day_night_cycle import DayNightCycle
from game.systems.fade_in_system import FadeInSystem
from game.managers.world_manager import WorldManager
from panda3d.core import Fog
import numpy as np

class EnvironmentManager:
    """
    Manages environmental effects, celestial bodies, and day/night cycle.
    """
    def __init__(self, world: World, renderer: Renderer, world_manager: WorldManager):
        self.world = world
        self.renderer = renderer
        self.world_manager = world_manager

    def setup(self, player_transform: Transform):
        """Initialize environment systems and entities."""
        self._setup_fog()
        sun, moon = self._create_celestial_bodies()
        self._setup_systems(sun, moon, player_transform)

    def _setup_fog(self):
        """Setup distance fog for performance and atmosphere."""
        fog = Fog("DistanceFog")
        fog.setColor(0.53, 0.8, 0.92) # Sky blue
        
        # Use fog radius from world manager
        density = 1.0 / self.world_manager.fog_radius
        fog.setExpDensity(density) 
        
        if hasattr(self.renderer.backend, 'scene_graph'):
            self.renderer.backend.scene_graph.setFog(fog)

    def _create_celestial_bodies(self):
        """Create visual entities for Sun and Moon."""
        # Sun (Sphere)
        sun = self.world.create_entity()
        sun.add_component(Transform())
        
        sun_renderer = MeshRenderer(
            mesh=create_sphere_mesh(radius=10.0, segments=32, rings=16), 
            color=(1.0, 1.0, 0.8, 1.0),
            texture_path="assets/textures/sun.png"
        )
        sun.add_component(sun_renderer)
        
        # Moon (Sphere)
        moon = self.world.create_entity()
        moon.add_component(Transform())
        
        moon_renderer = MeshRenderer(
            mesh=create_sphere_mesh(radius=8.0, segments=32, rings=16), 
            color=(0.8, 0.8, 1.0, 1.0),
            texture_path="assets/textures/moon.png"
        )
        moon.add_component(moon_renderer)
        
        return sun, moon

    def _setup_systems(self, sun, moon, player_transform):
        self.world.add_system(FadeInSystem())
        
        day_night = DayNightCycle(self.renderer)
        day_night.target = player_transform
        day_night.sun_entity = sun
        day_night.moon_entity = moon
        day_night.orbit_radius = self.world_manager.fog_radius - 50.0 
        self.world.add_system(day_night)
