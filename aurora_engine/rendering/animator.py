# aurora_engine/rendering/animator.py

from aurora_engine.ecs.component import Component
from aurora_engine.core.logging import get_logger
from typing import Dict, Optional, List

logger = get_logger()

class AnimationClip:
    """
    Represents a single animation clip (e.g., 'Walk', 'Idle').
    """
    def __init__(self, name: str, path: str = None, speed: float = 1.0, loop: bool = True):
        self.name = name
        self.path = path # Path to animation file if separate, or name in GLTF
        self.speed = speed
        self.loop = loop
        # Backend handle (Panda3D AnimControl)
        self._backend_handle = None

class Animator(Component):
    """
    Component for handling skeletal character animations.
    """
    def __init__(self):
        super().__init__()
        self.clips: Dict[str, AnimationClip] = {}
        self.current_clip: Optional[str] = None
        self.next_clip: Optional[str] = None
        self.blend_duration: float = 0.2
        self.blend_timer: float = 0.0
        self.playing = False
        
        # Backend reference (Panda3D Actor)
        self._actor = None

    def add_clip(self, name: str, path: str = None, speed: float = 1.0, loop: bool = True):
        """Register an animation clip."""
        self.clips[name] = AnimationClip(name, path, speed, loop)

    def play(self, name: str, blend: float = 0.2, force: bool = False):
        """Play an animation, optionally blending."""
        if name not in self.clips:
            logger.warning(f"Animation clip '{name}' not found.")
            return

        # If we are already playing this clip fully, do nothing
        if self.current_clip == name and self.next_clip is None and not force:
            return
            
        # If we are already blending TO this clip, do nothing (don't reset timer!)
        if self.next_clip == name and not force:
            return

        if self.current_clip is None:
            # Immediate play
            self.current_clip = name
            self.blend_timer = 0.0
            self._play_backend(name)
        else:
            # Blend
            self.next_clip = name
            self.blend_duration = blend
            self.blend_timer = 0.0
            # Backend blending logic handled in system
            if self._actor:
                self._actor.enableBlend()
                # Start the new animation but with 0 weight initially
                # We need to make sure it's playing so we can blend to it
                clip = self.clips[self.next_clip]
                self._actor.setPlayRate(clip.speed, self.next_clip)
                if clip.loop:
                    self._actor.loop(self.next_clip)
                else:
                    self._actor.play(self.next_clip)
                    
                self._actor.setControlEffect(self.current_clip, 1.0)
                self._actor.setControlEffect(self.next_clip, 0.0)
            
        self.playing = True

    def stop(self):
        """Stop current animation."""
        self.playing = False
        self.current_clip = None
        if self._actor:
            self._actor.stop()

    def _play_backend(self, name: str):
        """Internal: Trigger backend playback."""
        if not self._actor:
            return
            
        # Ensure we exit blend mode when playing a single animation
        self._actor.disableBlend()
            
        clip = self.clips[name]
        self._actor.setPlayRate(clip.speed, name)
        
        if clip.loop:
            self._actor.loop(name)
        else:
            self._actor.play(name)
