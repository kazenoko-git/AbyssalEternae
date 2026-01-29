# aurora_engine/input/action_map.py

from typing import Dict, List, Callable, Tuple
from enum import Enum


class InputDevice(Enum):
    KEYBOARD = 1
    MOUSE = 2
    GAMEPAD = 3


class Action:
    """Represents a gameplay action (e.g., 'Jump', 'Attack')."""

    def __init__(self, name: str):
        self.name = name
        self.bindings: List[Tuple[InputDevice, str]] = []  # [(device, key/button)]

    def add_binding(self, device: InputDevice, key: str):
        """Bind an input to this action."""
        self.bindings.append((device, key))


class ActionMap:
    """
    Maps raw input to high-level actions.
    Supports rebinding and multiple bindings per action.
    """

    def __init__(self):
        self.actions: Dict[str, Action] = {}

    def create_action(self, name: str) -> Action:
        """Create a new action."""
        action = Action(name)
        self.actions[name] = action
        return action

    def get_action(self, name: str) -> Action:
        """Get action by name."""
        return self.actions.get(name)

    def is_action_active(self, name: str, input_state: dict) -> bool:
        """Check if any binding for this action is pressed."""
        action = self.get_action(name)
        if not action:
            return False

        for device, key in action.bindings:
            if self._check_input(device, key, input_state):
                return True

        return False

    def _check_input(self, device: InputDevice, key: str, input_state: dict) -> bool:
        """Check if a specific input is pressed."""
        watcher = input_state.get('watcher')
        if not watcher:
            return False
            
        from panda3d.core import KeyboardButton, MouseButton
        
        btn = None
        if device == InputDevice.KEYBOARD:
            # Panda3D KeyboardButton
            try:
                if len(key) == 1:
                    btn = KeyboardButton.ascii_key(key)
                else:
                    # Handle special keys like "space", "shift", etc.
                    attr = getattr(KeyboardButton, key, None)
                    if callable(attr):
                        btn = attr() # Call the method to get the handle
                    else:
                        btn = attr
            except AttributeError:
                pass

        elif device == InputDevice.MOUSE:
            if key == "mouse1": btn = MouseButton.one()
            elif key == "mouse2": btn = MouseButton.two()
            elif key == "mouse3": btn = MouseButton.three()
            
        if btn:
            return watcher.isButtonDown(btn)
            
        # Fallback: check if key string works directly (Panda3D supports string lookup for some)
        return watcher.isButtonDown(key)
