# aurora_engine/camera/camera_controller.py

from abc import ABC, abstractmethod
from aurora_engine.camera.camera import Camera
from aurora_engine.core.logging import get_logger

logger = get_logger()

class CameraController(ABC):
    """
    Base class for camera control strategies.
    Controllers update camera position/rotation based on different logic.
    """

    def __init__(self, camera: Camera):
        self.camera = camera
        self.enabled = True
        # logger.debug(f"{self.__class__.__name__} initialized")

    @abstractmethod
    def update(self, dt: float, alpha: float = 1.0):
        """Update camera transform."""
        pass
