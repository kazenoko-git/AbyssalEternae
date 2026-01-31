# game/components/fade_in.py

from aurora_engine.ecs.component import Component
from aurora_engine.core.logging import get_logger

logger = get_logger()

class FadeInEffect(Component):
    """
    Component to handle fading in of entities.
    """

    def __init__(self, duration: float = 0.5):
        super().__init__()
        self.duration = duration
        self.elapsed = 0.0
        self.current_alpha = 0.0
        # logger.debug(f"FadeInEffect created (duration={duration}s)")
