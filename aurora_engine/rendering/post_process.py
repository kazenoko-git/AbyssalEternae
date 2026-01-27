# aurora_engine/rendering/post_process.py

from panda3d.core import Texture, Shader
from direct.filter.FilterManager import FilterManager
import logging

class PostProcessEffect:
    """
    Base class for post-processing effects.
    Examples: bloom, outline, color grading, cel-shading outlines.
    """

    def __init__(self, name: str):
        self.name = name
        self.enabled = True
        self.priority = 0  # Lower = earlier

    def apply(self, renderer):
        """Apply post-processing effect to screen buffer."""
        pass


class OutlineEffect(PostProcessEffect):
    """
    Cel-shading outline effect.
    Detects edges using depth/normal buffer and draws outlines.
    """

    def __init__(self, base=None):
        super().__init__("Outline")

        self.outline_color = (0.0, 0.0, 0.0, 1.0)
        self.outline_thickness = 1.5
        self.depth_threshold = 0.1
        self.normal_threshold = 0.4
        self.manager = None
        
        if base:
            self._initialize_manager(base)

    def _initialize_manager(self, base):
        """Initialize FilterManager once."""
        if not self.manager and base:
            try:
                self.manager = FilterManager(base.win, base.cam)
                
                # Request depth and normal textures
                tex_depth = Texture()
                tex_normal = Texture()
                
                # Create quad for post processing
                self.quad = self.manager.renderSceneInto(colortex=None, depthtex=tex_depth, auxtex=tex_normal)
                
                if self.quad:
                    # Placeholder shader setup
                    pass
            except Exception as e:
                logging.warning(f"Failed to initialize OutlineEffect: {e}")
                self.enabled = False

    def apply(self, renderer):
        """Apply outline detection shader."""
        # Manager is initialized in __init__ now
        pass


class BloomEffect(PostProcessEffect):
    """
    Bloom (glow) effect.
    Commonly used in anime-style games.
    """

    def __init__(self, base=None):
        super().__init__("Bloom")

        self.threshold = 0.8
        self.intensity = 0.5
        self.blur_passes = 5
        self.manager = None
        
        if base:
            self._initialize_manager(base)

    def _initialize_manager(self, base):
        """Initialize FilterManager once."""
        if not self.manager and base:
            try:
                self.manager = FilterManager(base.win, base.cam)
                tex = Texture()
                self.quad = self.manager.renderSceneInto(colortex=tex)
                
                if self.quad:
                    # Placeholder shader setup
                    pass
            except Exception as e:
                logging.warning(f"Failed to initialize BloomEffect: {e}")
                self.enabled = False

    def apply(self, renderer):
        """Apply bloom effect."""
        # Manager is initialized in __init__ now
        pass
