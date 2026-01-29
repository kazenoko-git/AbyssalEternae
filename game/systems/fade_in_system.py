# game/systems/fade_in_system.py

from aurora_engine.ecs.system import System
from aurora_engine.rendering.mesh import MeshRenderer
from game.components.fade_in import FadeInEffect
from panda3d.core import TransparencyAttrib
from aurora_engine.core.logging import get_logger

logger = get_logger()

class FadeInSystem(System):
    """
    System to update FadeInEffect components.
    """

    def __init__(self):
        super().__init__()
        # logger.debug("FadeInSystem initialized")

    def get_required_components(self):
        return [FadeInEffect, MeshRenderer]

    def update(self, entities, dt):
        for entity in entities:
            fade = entity.get_component(FadeInEffect)
            renderer = entity.get_component(MeshRenderer)
            
            if not hasattr(renderer, '_node_path') or not renderer._node_path:
                continue
                
            # Initialize transparency on first frame
            if fade.elapsed == 0.0:
                renderer._node_path.setTransparency(TransparencyAttrib.MAlpha)
                
            fade.elapsed += dt
            progress = min(1.0, fade.elapsed / fade.duration)
            fade.current_alpha = progress
            
            # Update alpha
            renderer._node_path.setAlphaScale(progress)
            
            # Remove component when done
            if progress >= 1.0:
                renderer._node_path.clearTransparency()
                entity.remove_component(FadeInEffect)
                # logger.debug(f"Fade-in complete for Entity {entity.id}")
