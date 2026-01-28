# game/components/fade_in.py

from aurora_engine.ecs.component import Component


class FadeInEffect(Component):
    """
    Component to handle fading in of entities.
    """

    def __init__(self, duration: float = 1.0):
        super().__init__()
        self.duration = duration
        self.elapsed = 0.0
        self.current_alpha = 0.0
