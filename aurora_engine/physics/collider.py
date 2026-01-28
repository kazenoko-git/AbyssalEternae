# aurora_engine/physics/collider.py

from aurora_engine.ecs.component import Component
import numpy as np


class ColliderShape:
    """Base collider shape."""
    pass


class BoxCollider(ColliderShape):
    """Box-shaped collider."""

    def __init__(self, size: np.ndarray):
        self.size = size


class SphereCollider(ColliderShape):
    """Sphere-shaped collider."""

    def __init__(self, radius: float):
        self.radius = radius


class HeightfieldCollider(ColliderShape):
    """
    Heightfield collider for terrain.
    Expects a 2D numpy array of height values.
    """
    def __init__(self, heightmap: np.ndarray, scale: float = 1.0):
        self.heightmap = heightmap
        self.scale = scale


class MeshCollider(ColliderShape):
    """
    Mesh-based collider (convex hull or triangle mesh).
    """
    def __init__(self, mesh, convex: bool = True):
        self.mesh = mesh
        self.convex = convex


class Collider(Component):
    """
    Collider component.
    Defines collision shape for physics/queries.
    """

    def __init__(self, shape: ColliderShape):
        super().__init__()

        self.shape = shape
        self.trigger = False  # If true, doesn't block movement
        self.offset = np.array([0.0, 0.0, 0.0], dtype=np.float32)

        # Collision filtering
        self.layer = 0
        self.mask = 0xFFFFFFFF

        # Callbacks
        self.on_collision_enter = None
        self.on_collision_exit = None