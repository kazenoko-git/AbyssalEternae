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

        # Adjusted speeds to match animation
        # Previous move_speed was 5.0. Previous sneak was 5.0 * 0.5 = 2.5.
        # User wants walking speed to match previous crouching speed (2.5).
        self.move_speed = 2.5 
        
        # User wants running speed slower than 10.0. Let's try 6.0.
        self.sprint_speed = 6.0

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
