# aurora_engine/core/time.py

import time


class TimeManager:
    """
    Central time management.
    Handles fixed timestep, delta time, frame counting.
    """

    def __init__(self, fixed_timestep: float = 1 / 60.0):
        self.fixed_delta = fixed_timestep  # Fixed physics timestep
        self.delta_time = 0.0  # Variable frame time
        self.time_scale = 1.0  # For slow-mo/speed-up

        # Timing
        self._last_frame_time = time.perf_counter()
        self._fixed_time = 0.0

        # Frame counting
        self.frame_count = 0
        self.fixed_frame_count = 0

        # FPS tracking
        self._fps_samples = []
        self._fps_sample_count = 60
        self.fps = 0.0

    def tick(self) -> float:
        """
        Call once per frame.
        Returns frame delta time.
        """
        current_time = time.perf_counter()
        self.delta_time = (current_time - self._last_frame_time) * self.time_scale
        self._last_frame_time = current_time

        # Update FPS
        self._fps_samples.append(self.delta_time)
        if len(self._fps_samples) > self._fps_sample_count:
            self._fps_samples.pop(0)

        if self._fps_samples:
            avg_delta = sum(self._fps_samples) / len(self._fps_samples)
            self.fps = 1.0 / avg_delta if avg_delta > 0 else 0.0

        self.frame_count += 1
        return self.delta_time

    def increment_fixed_time(self):
        """Call after each fixed update."""
        self._fixed_time += self.fixed_delta
        self.fixed_frame_count += 1

    def get_time(self) -> float:
        """Get total elapsed time (variable)."""
        return time.perf_counter()

    def get_fixed_time(self) -> float:
        """Get total fixed time."""
        return self._fixed_time