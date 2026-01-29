# aurora_engine/input/input_context.py

from typing import Dict, Callable
from aurora_engine.input.action_map import ActionMap
from aurora_engine.core.logging import get_logger

logger = get_logger()

class InputContext:
    """
    Input contexts allow different input mappings for different game states.
    Examples: UI context, gameplay context, cutscene context.
    """

    def __init__(self, name: str):
        self.name = name
        self.action_map = ActionMap()
        self.enabled = True

        # Callbacks for actions
        self.action_callbacks: Dict[str, Callable] = {}
        # logger.debug(f"InputContext '{name}' created")

    def bind_action_callback(self, action_name: str, callback: Callable):
        """Bind a callback to an action."""
        self.action_callbacks[action_name] = callback
        # logger.debug(f"Bound callback to action '{action_name}' in context '{self.name}'")

    def process_input(self, input_state: dict):
        """Process input for this context."""
        if not self.enabled:
            return

        for action_name, callback in self.action_callbacks.items():
            if self.action_map.is_action_active(action_name, input_state):
                callback()
