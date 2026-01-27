# aurora_engine/input/input_manager.py

from typing import List, Dict, Optional
from aurora_engine.input.input_context import InputContext
from aurora_engine.input.action_map import InputDevice
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import WindowProperties, MouseButton, KeyboardButton


class InputManager:
    """
    Central input coordinator.
    Manages contexts, polling, and dispatching.
    """

    def __init__(self):
        self.contexts: List[InputContext] = []
        self.active_context: Optional[InputContext] = None

        # Raw input state (polled each frame)
        self._input_state = {
            'keys': set(),
            'mouse_buttons': set(),
            'mouse_pos': (0.0, 0.0),
            'mouse_delta': (0.0, 0.0)
        }
        
        # We need access to Panda3D's input system.
        # Assuming ShowBase is initialized elsewhere and we can access `base`.
        # If not, we might need to pass it in or use global `base`.
        # For now, we'll assume `base` is available globally or we hook into it.
        
        self._setup_listeners()

    def _setup_listeners(self):
        """Setup Panda3D input listeners."""
        # In Panda3D, we usually use base.buttonThrowers or direct.showbase.DirectObject
        # But for a raw polling approach or event based, we can use the messenger.
        
        # However, to keep it simple and robust, we can use a polling approach 
        # combined with Panda's `is_button_down` if available, or track events.
        
        # Let's use a DirectObject to listen for all events if we want event-based,
        # but for `poll()` style, we might want to query `base.mouseWatcherNode`.
        pass

    def create_context(self, name: str) -> InputContext:
        """Create a new input context."""
        context = InputContext(name)
        self.contexts.append(context)
        return context

    def set_active_context(self, context: InputContext):
        """Switch to a different input context."""
        self.active_context = context

    def poll(self):
        """Poll hardware for input state."""
        # Access global base if available
        try:
            import builtins
            base = builtins.base
        except (ImportError, AttributeError):
            return

        if not base or not base.mouseWatcherNode:
            return

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

        # For keys, we can't easily iterate all keys in Panda3D without listeners.
        # So we rely on `is_button_down` checks in `ActionMap` or we maintain a set of pressed keys here.
        # Let's maintain a set of pressed keys using events.
        
        # Actually, `base.mouseWatcherNode.isButtonDown(key)` is efficient.
        # So we don't need to store all keys in `_input_state`, we just need to provide
        # a way to query it.
        
        # But `ActionMap` expects `input_state` dict. Let's pass the watcher node wrapper?
        # Or let `ActionMap` query `base` directly?
        # Better to abstract it.
        
        # Let's store a reference to the watcher node in input state for the ActionMap to use.
        self._input_state['watcher'] = base.mouseWatcherNode

    def update(self, dt: float):
        """Process input and dispatch to active context."""
        if self.active_context:
            self.active_context.process_input(self._input_state)
            
    def get_mouse_delta(self):
        return self._input_state.get('mouse_delta', (0.0, 0.0))
