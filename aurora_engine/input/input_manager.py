# aurora_engine/input/input_manager.py

from typing import List, Dict, Optional
from aurora_engine.input.input_context import InputContext
from aurora_engine.input.action_map import InputDevice
from aurora_engine.core.logging import get_logger


class InputManager:
    """
    Central input coordinator.
    Manages contexts, polling, and dispatching.
    """

    def __init__(self):
        self.contexts: List[InputContext] = []
        self.active_context: Optional[InputContext] = None
        self.backend = None # Reference to PandaBackend
        self.logger = get_logger()

        # Raw input state (polled each frame)
        self._input_state = {
            'keys': set(),
            'mouse_buttons': set(),
            'mouse_pos': (0.0, 0.0),
            'mouse_delta': (0.0, 0.0),
            'watcher': None
        }
        self.logger.info("InputManager initialized")

    def initialize(self, backend):
        """Initialize with backend reference."""
        self.backend = backend
        self.logger.info("InputManager initialized with backend")

    def create_context(self, name: str) -> InputContext:
        """Create a new input context."""
        context = InputContext(name)
        self.contexts.append(context)
        self.logger.info(f"Created input context: {name}")
        return context

    def set_active_context(self, context: InputContext):
        """Switch to a different input context."""
        if self.active_context and self.active_context.name == context.name:
            return
        self.active_context = context
        self.logger.info(f"Set active input context: {context.name}")

    def poll(self):
        """Poll hardware for input state."""
        if not self.backend or not self.backend.base:
            return

        base = self.backend.base
        if not base.mouseWatcherNode:
            return
            
        # Store watcher for ActionMap to use
        self._input_state['watcher'] = base.mouseWatcherNode

        # Update mouse position
        if base.mouseWatcherNode.hasMouse():
            mpos = base.mouseWatcherNode.getMouse()
            new_pos = (mpos.getX(), mpos.getY())
            
            # Calculate delta
            old_pos = self._input_state['mouse_pos']
            self._input_state['mouse_delta'] = (new_pos[0] - old_pos[0], new_pos[1] - old_pos[1])
            self._input_state['mouse_pos'] = new_pos
        else:
            self._input_state['mouse_delta'] = (0.0, 0.0)

    def update(self, dt: float):
        """Process input and dispatch to active context."""
        if self.active_context:
            self.active_context.process_input(self._input_state)
            
    def get_mouse_delta(self):
        return self._input_state.get('mouse_delta', (0.0, 0.0))
        
    def is_key_down(self, key: str) -> bool:
        """Directly check if a key is pressed."""
        if self._input_state['watcher']:
            return self._input_state['watcher'].isButtonDown(key)
        return False
