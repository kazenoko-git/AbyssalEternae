# aurora_engine/ui/theme.py

from typing import Dict, Any, TYPE_CHECKING
from aurora_engine.core.logging import get_logger

logger = get_logger()

if TYPE_CHECKING:
    from aurora_engine.ui.widget import Widget


class UITheme:
    """
    UI theme definition.
    Allows consistent styling across all widgets.
    """

    def __init__(self, name: str):
        self.name = name

        # Color palette
        self.colors: Dict[str, tuple] = {
            'primary': (0.2, 0.4, 0.8, 1.0),
            'secondary': (0.3, 0.3, 0.3, 1.0),
            'background': (0.1, 0.1, 0.1, 0.9),
            'text': (1.0, 1.0, 1.0, 1.0),
            'text_disabled': (0.5, 0.5, 0.5, 1.0),
            'border': (0.5, 0.5, 0.5, 1.0),
            'hover': (0.3, 0.5, 0.9, 1.0),
            'pressed': (0.15, 0.3, 0.6, 1.0),
        }

        # Font settings
        self.fonts: Dict[str, Any] = {
            'default': 'Arial',
            'title': 'Arial Bold',
            'mono': 'Courier New',
        }

        # Sizes
        self.sizes: Dict[str, float] = {
            'font_small': 12,
            'font_normal': 16,
            'font_large': 24,
            'font_title': 32,
            'padding': 10,
            'margin': 5,
            'border_width': 2,
        }
        # logger.debug(f"UITheme '{name}' initialized")

    def get_color(self, name: str) -> tuple:
        """Get color by name."""
        return self.colors.get(name, (1.0, 1.0, 1.0, 1.0))

    def apply_to_widget(self, widget: 'Widget'):
        """Apply theme to a widget."""
        # Override in specific implementations
        pass


class GenshinTheme(UITheme):
    """Genshin Impact-inspired theme."""

    def __init__(self):
        super().__init__("Genshin")

        # Genshin-style colors
        self.colors = {
            'primary': (0.9, 0.7, 0.3, 1.0),  # Gold
            'secondary': (0.2, 0.3, 0.5, 1.0),  # Dark blue
            'background': (0.05, 0.05, 0.15, 0.95),  # Very dark blue
            'text': (0.95, 0.95, 0.95, 1.0),
            'text_disabled': (0.5, 0.5, 0.6, 1.0),
            'border': (0.8, 0.6, 0.2, 1.0),  # Gold border
            'hover': (1.0, 0.8, 0.4, 1.0),
            'pressed': (0.7, 0.5, 0.1, 1.0),
        }
