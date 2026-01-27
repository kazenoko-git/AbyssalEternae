# aurora_engine/camera/camera_shake.py

import numpy as np
import random


class CameraShake:
    """
    Camera shake effect.
    Adds procedural shake to camera for impacts, explosions, etc.
    """

    def __init__(self):
        self.active = False
        self.intensity = 0.0
        self.duration = 0.0
        self.elapsed = 0.0

        # Shake parameters
        self.frequency = 25.0  # Hz
        self.roughness = 1.0

        # Current shake offset
        self.offset = np.zeros(3, dtype=np.float32)

        # Trauma-based shake (better feeling)
        self.trauma = 0.0
        self.trauma_decay = 1.0

    def add_trauma(self, amount: float):
        """
        Add trauma (0-1) to camera.
        Trauma decays over time and creates shake.
        """
        self.trauma = min(1.0, self.trauma + amount)

    def trigger(self, intensity: float, duration: float):
        """Trigger a camera shake."""
        self.active = True
        self.intensity = intensity
        self.duration = duration
        self.elapsed = 0.0

    def update(self, dt: float):
        """Update shake effect."""
        if self.trauma > 0:
            # Decay trauma
            self.trauma = max(0, self.trauma - self.trauma_decay * dt)

            # Generate shake from trauma
            shake = self.trauma * self.trauma  # Square for better feel

            self.offset[0] = shake * self.intensity * (random.random() * 2 - 1)
            self.offset[1] = shake * self.intensity * (random.random() * 2 - 1)
            self.offset[2] = shake * self.intensity * (random.random() * 2 - 1)

        elif self.active:
            # Time-based shake
            self.elapsed += dt

            if self.elapsed >= self.duration:
                self.active = False
                self.offset = np.zeros(3, dtype=np.float32)
                return

            # Falloff over time
            falloff = 1.0 - (self.elapsed / self.duration)

            # Perlin-like noise
            angle = self.elapsed * self.frequency * 2 * np.pi

            self.offset[0] = np.sin(angle) * self.intensity * falloff * (random.random() * 2 - 1)
            self.offset[1] = np.cos(angle * 1.3) * self.intensity * falloff * (random.random() * 2 - 1)
            self.offset[2] = np.sin(angle * 0.7) * self.intensity * falloff * (random.random() * 2 - 1)

    def get_offset(self) -> np.ndarray:
        """Get current shake offset."""
        return self.offset.copy()

    def reset(self):
        """Reset shake."""
        self.active = False
        self.trauma = 0.0
        self.offset = np.zeros(3, dtype=np.float32)