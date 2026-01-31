# game_project/components/player.py

from aurora_engine.ecs.component import Component
from aurora_engine.core.logging import get_logger

logger = get_logger()

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
        
        # State Flags
        self.is_sprinting = False
        self.is_sneaking = False
        self.is_blocking = False
        self.is_attacking = False
        self.is_aiming = False # Zoom
        
        # Cooldowns / Timers
        self.attack_cooldown = 0.0
        self.block_stamina = 100.0

        # logger.debug("PlayerController created")
