# aurora_engine/ui/animator.py

from typing import Callable, Dict, Any, Optional
import math


class UIAnimation:
    """
    Represents a single UI animation (e.g., fade in, slide).
    """

    def __init__(self, target: Any, property_name: str, start_val: float, end_val: float, duration: float, curve: str = "linear"):
        self.target = target
        self.property_name = property_name
        self.start_val = start_val
        self.end_val = end_val
        self.duration = duration
        self.curve = curve
        
        self.elapsed = 0.0
        self.finished = False
        self.on_complete: Optional[Callable] = None

    def update(self, dt: float):
        """Update animation state."""
        if self.finished:
            return

        self.elapsed += dt
        t = min(1.0, self.elapsed / self.duration)
        
        # Apply easing
        t_eased = self._ease(t)
        
        # Interpolate
        current_val = self.start_val + (self.end_val - self.start_val) * t_eased
        
        # Apply to target
        if hasattr(self.target, self.property_name):
            setattr(self.target, self.property_name, current_val)
        elif isinstance(self.target, dict):
            self.target[self.property_name] = current_val

        if self.elapsed >= self.duration:
            self.finished = True
            if self.on_complete:
                self.on_complete()

    def _ease(self, t: float) -> float:
        """Apply easing function."""
        if self.curve == "linear":
            return t
        elif self.curve == "ease_in":
            return t * t
        elif self.curve == "ease_out":
            return t * (2 - t)
        elif self.curve == "ease_in_out":
            return t * t * (3 - 2 * t)
        elif self.curve == "elastic":
            return math.sin(-13 * (t + 1) * math.pi / 2) * math.pow(2, -10 * t) + 1
        return t


class UIAnimator:
    """
    Manages UI animations.
    """

    def __init__(self):
        self.animations: List[UIAnimation] = []

    def animate(self, target: Any, property_name: str, end_val: float, duration: float, curve: str = "linear", on_complete: Callable = None):
        """Start a new animation."""
        # Get start value
        start_val = 0.0
        if hasattr(target, property_name):
            start_val = getattr(target, property_name)
        elif isinstance(target, dict):
            start_val = target.get(property_name, 0.0)
            
        anim = UIAnimation(target, property_name, start_val, end_val, duration, curve)
        anim.on_complete = on_complete
        
        # Remove existing animations on same property
        self.animations = [a for a in self.animations if not (a.target == target and a.property_name == property_name)]
        
        self.animations.append(anim)

    def update(self, dt: float):
        """Update all active animations."""
        for anim in self.animations[:]:
            anim.update(dt)
            if anim.finished:
                self.animations.remove(anim)
