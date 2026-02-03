# game/systems/fade_in_system.py

from aurora_engine.ecs.system import System
from aurora_engine.rendering.mesh import MeshRenderer
from game.components.fade_in import FadeInEffect
from aurora_engine.core.logging import get_logger

logger = get_logger()

class FadeInSystem(System):
    """
    Manages the fade-in effect for newly spawned entities.
    """

    def get_required_components(self):
        return [FadeInEffect, MeshRenderer]

    def update(self, entities, dt):
        for entity in entities:
            fade = entity.get_component(FadeInEffect)
            renderer = entity.get_component(MeshRenderer)
            
            if fade.elapsed < fade.duration:
                fade.elapsed += dt
                alpha = min(1.0, fade.elapsed / fade.duration)
                
                # Update transparency
                # Assuming renderer has a way to set alpha or color
                # If color is (r, g, b, a)
                if hasattr(renderer, 'color'):
                    current_color = list(renderer.color)
                    if len(current_color) == 4:
                        # Interpolate alpha from 0 to target (usually 1.0)
                        # But we don't know original alpha. Let's assume 1.0 target.
                        current_color[3] = alpha
                        renderer.color = tuple(current_color)
                        
                        # Update backend node transparency
                        if hasattr(renderer, '_node_path') and renderer._node_path:
                            renderer._node_path.setTransparency(True)
                            renderer._node_path.setAlphaScale(alpha)
            else:
                # Fade complete
                entity.remove_component(FadeInEffect)
                # Ensure full opacity
                if hasattr(renderer, '_node_path') and renderer._node_path:
                    renderer._node_path.clearTransparency()
                    renderer._node_path.setAlphaScale(1.0)
