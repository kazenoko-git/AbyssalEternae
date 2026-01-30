# aurora_engine/input/input_manager.py

from typing import List, Dict, Optional
from aurora_engine.input.input_context import InputContext
from aurora_engine.input.action_map import InputDevice
from aurora_engine.core.logging import get_logger
from aurora_engine.utils.profiler import profile_section


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
        self.mouse_locked = False

        # Raw input state (polled each frame)
        self._input_state = {
            'keys': set(),
            'mouse_buttons': set(),
            'mouse_pos': (0.0, 0.0),
            'mouse_delta': (0.0, 0.0),
            'watcher': None
        }
        
        # Anti-drift state
        self._last_mouse_pos = (0, 0)
        self._ignore_next_mouse_delta = False
        
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

    def set_mouse_lock(self, locked: bool):
        """Lock or unlock the mouse cursor to the center of the screen."""
        self.mouse_locked = locked
        if self.backend and self.backend.window:
            from panda3d.core import WindowProperties
            props = WindowProperties()
            props.setCursorHidden(locked)
            
            # Use Absolute mode + Manual Centering for most reliable control
            props.setMouseMode(WindowProperties.M_absolute)
                
            self.backend.window.requestProperties(props)
            
            if locked:
                # Center immediately
                w = self.backend.window.getXSize()
                h = self.backend.window.getYSize()
                if w > 0 and h > 0:
                    cx, cy = w // 2, h // 2
                    self.backend.window.movePointer(0, cx, cy)
                    self._last_mouse_pos = (cx, cy)
                    
                # Ignore the next delta calculation to prevent jump from previous position
                self._ignore_next_mouse_delta = True
            
            # Reset delta on mode switch to prevent jumps
            self._input_state['mouse_delta'] = (0.0, 0.0)

    def poll(self):
        """Poll hardware for input state."""
        if not self.backend or not self.backend.base:
            return

        base = self.backend.base
        win = self.backend.window
        
        # Store watcher for ActionMap to use
        if base.mouseWatcherNode:
            self._input_state['watcher'] = base.mouseWatcherNode

        if self.mouse_locked:
            # Manual centering approach for infinite rotation
            md = win.getPointer(0)
            x = md.getX()
            y = md.getY()
            
            w = win.getXSize()
            h = win.getYSize()
            
            if w > 0 and h > 0:
                cx, cy = w // 2, h // 2
                
                # Calculate delta from center
                dx = x - cx
                dy = y - cy
                
                # Anti-drift: If mouse hasn't moved since last read, ignore delta.
                # This handles cases where movePointer is lazy/deferred.
                if (x, y) == self._last_mouse_pos:
                    dx = 0
                    dy = 0
                
                self._last_mouse_pos = (x, y)
                
                if self._ignore_next_mouse_delta:
                    dx = 0
                    dy = 0
                    self._ignore_next_mouse_delta = False
                    # Force re-center just in case
                    win.movePointer(0, cx, cy)
                elif dx != 0 or dy != 0:
                    # Only move pointer if we actually moved
                    win.movePointer(0, cx, cy)
                    # Normalize to -1..1 range roughly
                    # Negate Y because window coords are Top-Left origin
                    self._input_state['mouse_delta'] = (dx / w * 2.0, -dy / h * 2.0)
                else:
                    self._input_state['mouse_delta'] = (0.0, 0.0)
        else:
            # Standard absolute mouse mode
            if not base.mouseWatcherNode:
                return

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
