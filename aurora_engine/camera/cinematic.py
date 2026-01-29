# aurora_engine/camera/cinematic.py

from typing import List
import numpy as np
from aurora_engine.camera.camera_controller import CameraController
from aurora_engine.core.logging import get_logger

logger = get_logger()

class CameraKeyframe:
    """A single keyframe in a camera animation."""

    def __init__(self, time: float, position: np.ndarray, rotation: np.ndarray, fov: float = 60.0):
        self.time = time
        self.position = position
        self.rotation = rotation
        self.fov = fov


class CinematicController(CameraController):
    """
    Cinematic camera controller.
    Plays back scripted camera animations.
    """

    def __init__(self, camera):
        super().__init__(camera)

        self.keyframes: List[CameraKeyframe] = []
        self.playback_time = 0.0
        self.playing = False
        self.loop = False
        # logger.debug("CinematicController initialized")

    def add_keyframe(self, keyframe: CameraKeyframe):
        """Add a keyframe to the animation."""
        self.keyframes.append(keyframe)
        # Sort by time
        self.keyframes.sort(key=lambda k: k.time)

    def play(self):
        """Start playback."""
        self.playing = True
        self.playback_time = 0.0
        logger.info("Started cinematic playback")

    def stop(self):
        """Stop playback."""
        self.playing = False
        logger.info("Stopped cinematic playback")

    def update(self, dt: float):
        """Update camera from keyframes."""
        if not self.playing or len(self.keyframes) < 2:
            return

        self.playback_time += dt

        # Find current keyframe segment
        current_kf, next_kf = self._get_current_segment()

        if not current_kf or not next_kf:
            if self.loop:
                self.playback_time = 0.0
            else:
                self.stop()
            return

        # Interpolate between keyframes
        t = (self.playback_time - current_kf.time) / (next_kf.time - current_kf.time)
        t = np.clip(t, 0.0, 1.0)

        # Smooth interpolation (ease in-out)
        t_smooth = t * t * (3.0 - 2.0 * t)

        # Interpolate position
        position = current_kf.position + t_smooth * (next_kf.position - current_kf.position)
        self.camera.transform.set_world_position(position)

        # Interpolate rotation (should use slerp for quaternions)
        # TODO: Proper quaternion interpolation

        # Interpolate FOV
        fov = current_kf.fov + t_smooth * (next_kf.fov - current_kf.fov)
        self.camera.field_of_view = fov

    def _get_current_segment(self):
        """Find keyframes to interpolate between."""
        for i in range(len(self.keyframes) - 1):
            if self.keyframes[i].time <= self.playback_time < self.keyframes[i + 1].time:
                return self.keyframes[i], self.keyframes[i + 1]
        return None, None
