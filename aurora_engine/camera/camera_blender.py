# aurora_engine/camera/camera_blender.py

from typing import Optional
from aurora_engine.camera.camera import Camera
import numpy as np


class CameraBlender:
    """
    Blends between cameras with smooth transitions.
    Used for cutscenes, entering vehicles, etc.
    """

    def __init__(self):
        self.current_camera: Optional[Camera] = None
        self.target_camera: Optional[Camera] = None

        self.blend_duration = 1.0
        self.blend_timer = 0.0
        self.blending = False

        # Blend curve (ease-in-out)
        self.blend_curve = lambda t: t * t * (3.0 - 2.0 * t)

    def blend_to(self, target_camera: Camera, duration: float = 1.0):
        """Start blending to a new camera."""
        self.target_camera = target_camera
        self.blend_duration = duration
        self.blend_timer = 0.0
        self.blending = True

    def update(self, dt: float, output_camera: Camera):
        """Update blend and write to output camera."""
        if not self.blending:
            if self.current_camera:
                self._copy_camera(self.current_camera, output_camera)
            return

        self.blend_timer += dt
        t = min(self.blend_timer / self.blend_duration, 1.0)
        t_smoothed = self.blend_curve(t)

        # Interpolate position
        pos_a = self.current_camera.transform.get_world_position()
        pos_b = self.target_camera.transform.get_world_position()
        blended_pos = pos_a + t_smoothed * (pos_b - pos_a)

        output_camera.transform.set_world_position(blended_pos)

        # TODO: Interpolate rotation (slerp quaternions)
        # TODO: Interpolate FOV

        # Finish blend
        if t >= 1.0:
            self.current_camera = self.target_camera
            self.blending = False

    def _copy_camera(self, source: Camera, dest: Camera):
        """Copy camera state."""
        dest.transform.set_world_position(source.transform.get_world_position())
        # TODO: Copy rotation, FOV