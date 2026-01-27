# aurora_engine/ui/ui_manager.py

from typing import List, Dict, Optional
import numpy as np
from aurora_engine.ui.widget import Widget
from aurora_engine.ui.theme import UITheme


class UIManager:
    """
    Central UI coordinator.
    Manages UI hierarchy, input, and rendering.
    """

    def __init__(self):
        # Root widgets (top-level UI elements)
        self.root_widgets: List[Widget] = []

        # Active theme
        self.theme: Optional[UITheme] = None

        # Input state
        self.mouse_position = np.array([0, 0], dtype=np.float32)
        self.focused_widget: Optional[Widget] = None

        # UI layers (for z-ordering)
        self.layers: Dict[str, List[Widget]] = {
            'background': [],
            'game': [],
            'hud': [],
            'menu': [],
            'overlay': [],
        }

    def initialize(self):
        """Initialize UI system."""
        # from aurora_engine.ui.theme import GenshinTheme
        # self.theme = GenshinTheme()
        pass

    def add_widget(self, widget: Widget, layer: str = 'hud'):
        """Add a widget to the UI."""
        if layer in self.layers:
            self.layers[layer].append(widget)
        else:
            self.root_widgets.append(widget)

        # Apply theme
        if self.theme:
            self.theme.apply_to_widget(widget)

    def remove_widget(self, widget: Widget):
        """Remove a widget from the UI."""
        for layer_widgets in self.layers.values():
            if widget in layer_widgets:
                layer_widgets.remove(widget)
                return

        if widget in self.root_widgets:
            self.root_widgets.remove(widget)

    def update(self, dt: float):
        """Update all UI widgets."""
        # Update in layer order
        for layer in ['background', 'game', 'hud', 'menu', 'overlay']:
            for widget in self.layers[layer]:
                widget.update(dt)

        # Process input
        self._process_input()

    def render(self):
        """Render all UI widgets."""
        for layer in ['background', 'game', 'hud', 'menu', 'overlay']:
            for widget in self.layers[layer]:
                widget.render()

    def _process_input(self):
        """Handle UI input (clicks, hovers)."""
        # Check hover state
        hovered_widget = self._get_widget_at_position(self.mouse_position)

        # Update hover states
        for layer_widgets in self.layers.values():
            for widget in layer_widgets:
                widget.hovered = (widget == hovered_widget)

    def _get_widget_at_position(self, position: np.ndarray) -> Optional[Widget]:
        """Find topmost widget at screen position."""
        # Check layers in reverse order (top to bottom)
        for layer in reversed(['overlay', 'menu', 'hud', 'game', 'background']):
            for widget in reversed(self.layers[layer]):
                if self._point_in_widget(position, widget):
                    return widget
        return None

    def _point_in_widget(self, point: np.ndarray, widget: Widget) -> bool:
        """Check if point is inside widget bounds."""
        if not widget.visible or not widget.enabled:
            return False

        pos = widget.get_screen_position()
        size = widget.size

        return (pos[0] <= point[0] <= pos[0] + size[0] and
                pos[1] <= point[1] <= pos[1] + size[1])
