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
        
        # Anti-drift / DPI-safe state
        self._last_mouse_pos = (0, 0)
        self._skip_next_delta = False
        
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
        """Lock or unlock the mouse cursor."""
        self.mouse_locked = locked
        if self.backend and self.backend.window:
            from panda3d.core import WindowProperties
            props = WindowProperties()
            props.setCursorHidden(locked)
            
            # Use Absolute mode. Relative mode can be buggy on secondary displays (macOS/Windows).
            # We will handle centering manually with a DPI-safe algorithm.
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
                    self._skip_next_delta = True
            
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
            md = win.getPointer(0)
            x = md.getX()
            y = md.getY()
            
            w = win.getXSize()
            h = win.getYSize()
            
            # DPI-Safe Delta Calculation:
            # We calculate delta based on the *previous frame's actual position*.
            # We do NOT assume the mouse is at the center.
            # We only re-center when the mouse gets too close to the edge.
            # When we re-center, we skip the next frame's delta to avoid the "jump" caused by 
            # coordinate system mismatches (DPI scaling) on secondary monitors.
            
            if self._skip_next_delta:
                dx = 0
                dy = 0
                self._skip_next_delta = False
                self._last_mouse_pos = (x, y)
            else:
                dx = x - self._last_mouse_pos[0]
                dy = y - self._last_mouse_pos[1]
                self._last_mouse_pos = (x, y)
            
            # Normalize delta
            if w > 0 and h > 0:
                # Negate Y because window coords are Top-Left origin
                self._input_state['mouse_delta'] = (dx / w * 2.0, -dy / h * 2.0)
            else:
                self._input_state['mouse_delta'] = (0.0, 0.0)
                
            # Re-center if near edge (Edge Reset)
            # This prevents running out of screen space while avoiding constant re-centering jitter
            margin = 100
            if x < margin or x > w - margin or y < margin or y > h - margin:
                if w > 0 and h > 0:
                    cx, cy = w // 2, h // 2
                    win.movePointer(0, cx, cy)
                    # Important: Skip next delta because 'x' next frame will jump to 'cx' (or scaled cx)
                    self._skip_next_delta = True

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
