# game_project/components/player.py

from aurora_engine.ecs.component import Component


class PlayerController(Component):
    """
    Player-specific component.
    This is GAME code, not ENGINE code.
    """

    def __init__(self):
        super().__init__()

        self.move_speed = 5.0
        self.sprint_speed = 10.0
        self.jump_force = 8.0

        self.inventory = []
        self.health = 100
        self.max_health = 100