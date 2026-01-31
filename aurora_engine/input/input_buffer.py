# aurora_engine/input/input_buffer.py

from collections import deque
from typing import Deque, Tuple
import time
from aurora_engine.core.logging import get_logger

logger = get_logger()

class InputEvent:
    """Represents a single input event."""

    def __init__(self, action: str, pressed: bool, timestamp: float):
        self.action = action
        self.pressed = pressed
        self.timestamp = timestamp


class InputBuffer:
    """
    Buffers input events for combo detection and input forgiveness.
    Critical for fighting games and action games.
    """

    def __init__(self, buffer_duration: float = 0.1):
        self.buffer_duration = buffer_duration
        self.events: Deque[InputEvent] = deque()

    def add_event(self, action: str, pressed: bool):
        """Add an input event to the buffer."""
        event = InputEvent(action, pressed, time.perf_counter())
        self.events.append(event)
        # logger.debug(f"Buffered input event: {action} {'pressed' if pressed else 'released'}")

    def update(self):
        """Remove old events from buffer."""
        current_time = time.perf_counter()

        while self.events and (current_time - self.events[0].timestamp) > self.buffer_duration:
            self.events.popleft()

    def check_sequence(self, sequence: list) -> bool:
        """
        Check if a sequence of actions exists in buffer.
        Example: ['down', 'down_forward', 'forward', 'punch'] for hadouken
        """
        if len(sequence) > len(self.events):
            return False

        # Check last N events match sequence
        recent_events = list(self.events)[-len(sequence):]

        for i, action in enumerate(sequence):
            if i >= len(recent_events) or recent_events[i].action != action:
                return False

        return True

    def was_pressed_recently(self, action: str, time_window: float = 0.05) -> bool:
        """
        Check if action was pressed within time window.
        Implements "input forgiveness".
        """
        current_time = time.perf_counter()

        for event in reversed(self.events):
            if (current_time - event.timestamp) > time_window:
                break

            if event.action == action and event.pressed:
                return True

        return False

    def clear(self):
        """Clear all buffered events."""
        self.events.clear()
