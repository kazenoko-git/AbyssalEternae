# aurora_engine/camera/camera_controller.py

from abc import ABC, abstractmethod
from aurora_engine.camera.camera import Camera


class CameraController(ABC):
    """
    Base class for camera control strategies.
    Controllers update camera position/rotation based on different logic.
    """

    def __init__(self, camera: Camera):
        self.camera = camera
        self.enabled = True

    @abstractmethod
    def update(self, dt: float):
        """Update camera transform."""
        pass