# aurora_engine/rendering/pipeline.py

from typing import List, Dict, Any
from aurora_engine.rendering.material import Material
from aurora_engine.rendering.post_process import PostProcessEffect


class RenderPass:
    """A single rendering pass (e.g., shadow pass, main pass, post-process)."""

    def __init__(self, name: str):
        self.name = name
        self.enabled = True
        self.clear_color = (0.0, 0.0, 0.0, 1.0)
        self.clear_depth = True

    def execute(self, renderer):
        """Execute this render pass."""
        pass


class RenderPipeline:
    """
    Defines the rendering pipeline structure.
    Supports forward rendering with multiple passes.
    """

    def __init__(self):
        self.passes: List[RenderPass] = []
        self.post_effects: List[PostProcessEffect] = []

        # Render targets
        self.render_targets: Dict[str, Any] = {}

    def add_pass(self, render_pass: RenderPass):
        """Add a render pass."""
        self.passes.append(render_pass)

    def add_post_effect(self, effect: PostProcessEffect):
        """Add post-processing effect."""
        self.post_effects.append(effect)

    def execute(self, renderer):
        """Execute all render passes."""
        for render_pass in self.passes:
            if render_pass.enabled:
                render_pass.execute(renderer)

        # Apply post-processing
        for effect in self.post_effects:
            if effect.enabled:
                effect.apply(renderer)
