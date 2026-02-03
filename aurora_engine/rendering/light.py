# aurora_engine/rendering/light.py

from aurora_engine.ecs.component import Component
import numpy as np
from typing import Tuple

class Light(Component):
    """
    Base class for all light components.
    """
    def __init__(self):
        super().__init__()
        self.color: np.ndarray = np.array([1.0, 1.0, 1.0], dtype=np.float32)
        self.intensity: float = 1.0
        
        # Backend handle (e.g., Panda3D Light NodePath)
        self._backend_handle = None

class AmbientLight(Light):
    """
    Represents an ambient light source that illuminates the entire scene evenly.
    """
    def __init__(self, color: Tuple[float, float, float] = (1.0, 1.0, 1.0), intensity: float = 1.0):
        super().__init__()
        self.color = np.array(color, dtype=np.float32)
        self.intensity = intensity

class DirectionalLight(Light):
    """
    Represents a directional light, like the sun or moon.
    It has a direction but no position.
    """
    def __init__(self, color: Tuple[float, float, float] = (1.0, 1.0, 1.0), intensity: float = 1.0):
        super().__init__()
        self.color = np.array(color, dtype=np.float32)
        self.intensity = intensity
        
        # Shadow properties
        self.cast_shadows: bool = True
        self.shadow_map_size: int = 2048
        self.shadow_film_size: float = 200.0
        self.shadow_near_far: Tuple[float, float] = (10.0, 1000.0)

class PointLight(Light):
    """
    Represents a point light source that emits light in all directions from a single point.
    """
    def __init__(self, color: Tuple[float, float, float] = (1.0, 1.0, 1.0), intensity: float = 1.0, radius: float = 10.0):
        super().__init__()
        self.color = np.array(color, dtype=np.float32)
        self.intensity = intensity
        self.radius = radius # Used for attenuation calculation
        
        # (Constant, Linear, Quadratic)
        self.attenuation: Tuple[float, float, float] = (1.0, 0.0, 0.0)
