# game_project/components/npc.py

from aurora_engine.ecs.component import Component
from aurora_engine.core.logging import get_logger

logger = get_logger()

class NPCController(Component):
    """
    NPC-specific component.
    Stores NPC identity and state.
    """

    def __init__(self, npc_id: str = "", npc_name: str = "NPC"):
        super().__init__()
        self.npc_id = npc_id
        self.npc_name = npc_name
        self.dialogue_state = "idle"
        self.current_target = None
        self.patrol_points = []
        # logger.debug(f"NPCController created for {npc_name} ({npc_id})")
