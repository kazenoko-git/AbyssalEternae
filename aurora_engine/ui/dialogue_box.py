# aurora_engine/ui/dialogue_box.py

from aurora_engine.ui.widget import Panel, Label, Button
from typing import List
import numpy as np
from aurora_engine.core.logging import get_logger

logger = get_logger()

class DialogueBox(Panel):
    """
    Specialized widget for displaying NPC dialogue.
    Supports text animation, choices, portraits.
    """

    def __init__(self):
        super().__init__("DialogueBox")

        # Sizing
        self.size = np.array([800, 200], dtype=np.float32)
        self.position = np.array([0, -300], dtype=np.float32)
        self.anchor = np.array([0.5, 1.0], dtype=np.float32)  # Bottom center

        # Components
        self.speaker_label = Label("Speaker", "")
        self.speaker_label.font_size = 18
        self.add_child(self.speaker_label)

        self.text_label = Label("Text", "")
        self.text_label.font_size = 16
        self.add_child(self.text_label)

        # Text animation
        self.full_text = ""
        self.displayed_text = ""
        self.text_speed = 30.0  # Characters per second
        self.text_progress = 0.0

        # Choices
        self.choices: List[str] = []
        self.choice_buttons: List[Button] = []
        # logger.debug("DialogueBox initialized")

    def show_dialogue(self, speaker: str, text: str):
        """Display new dialogue."""
        self.speaker_label.text = speaker
        self.full_text = text
        self.displayed_text = ""
        self.text_progress = 0.0
        self.visible = True
        # logger.debug(f"Showing dialogue: {speaker}: {text[:20]}...")

    def add_choice(self, choice_text: str, callback):
        """Add a dialogue choice button."""
        button = Button(f"Choice{len(self.choices)}", choice_text)
        button.on_click = callback
        self.add_child(button)

        self.choices.append(choice_text)
        self.choice_buttons.append(button)

        self._layout_choices()

    def _layout_choices(self):
        """Arrange choice buttons vertically."""
        y_offset = 60
        for i, button in enumerate(self.choice_buttons):
            button.position = np.array([0, y_offset + i * 40], dtype=np.float32)
            button.size = np.array([400, 35], dtype=np.float32)

    def update(self, dt: float):
        """Animate text reveal."""
        super().update(dt)

        if self.text_progress < len(self.full_text):
            self.text_progress += self.text_speed * dt
            char_count = int(self.text_progress)
            self.displayed_text = self.full_text[:char_count]
            self.text_label.text = self.displayed_text

    def skip_animation(self):
        """Instantly show full text."""
        self.text_progress = len(self.full_text)
        self.displayed_text = self.full_text
        self.text_label.text = self.displayed_text

    def clear_choices(self):
        """Remove all choice buttons."""
        for button in self.choice_buttons:
            self.remove_child(button)

        self.choices.clear()
        self.choice_buttons.clear()
