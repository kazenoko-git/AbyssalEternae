# aurora_engine/camera/camera_constraint.py

from abc import ABC, abstractmethod
import numpy as np
from aurora_engine.camera.camera import Camera
from aurora_engine.scene.transform import Transform
from aurora_engine.core.logging import get_logger

logger = get_logger()

class CameraConstraint(ABC):
    """
    Base class for camera constraints.
    Constraints modify camera position/rotation after controller updates.
    """

    def __init__(self):
        self.enabled = True
        self.priority = 0

    @abstractmethod
    def apply(self, camera: Camera, dt: float):
        """Apply constraint to camera."""
        pass


class CollisionConstraint(CameraConstraint):
    """
    Prevents camera from clipping through walls.
    Moves camera forward if blocked.
    """

    def __init__(self, physics_world):
        super().__init__()
        self.physics_world = physics_world
        self.collision_radius = 0.2

    def apply(self, camera: Camera, dt: float):
        """Check for collisions and adjust position."""
        from aurora_engine.physics.raycast import raycast

        camera_pos = camera.transform.get_world_position()

        # Get target position (where controller wants camera)
        # Cast ray from target to camera
        # If hit, move camera forward

        # TODO: Implement raycast-based collision
        pass


class BoundsConstraint(CameraConstraint):
    """
    Keeps camera within defined bounds.
    Useful for limiting camera movement in enclosed areas.
    """

    def __init__(self, min_bounds: np.ndarray, max_bounds: np.ndarray):
        super().__init__()
        self.min_bounds = min_bounds
        self.max_bounds = max_bounds

    def apply(self, camera: Camera, dt: float):
        """Clamp camera position to bounds."""
        pos = camera.transform.get_world_position()
        clamped = np.clip(pos, self.min_bounds, self.max_bounds)
        camera.transform.set_world_position(clamped)


class LookAtConstraint(CameraConstraint):
    """
    Forces camera to always look at a target.
    """

    def __init__(self, target: Transform):
        super().__init__()
        self.target = target

    def apply(self, camera: Camera, dt: float):
        """Rotate camera to look at target."""
        camera_pos = camera.transform.get_world_position()
        target_pos = self.target.get_world_position()

        # Calculate look direction
        direction = target_pos - camera_pos
        direction = direction / np.linalg.norm(direction)

        # Convert to rotation (quaternion)
        # TODO: Implement look-at rotation
        pass
