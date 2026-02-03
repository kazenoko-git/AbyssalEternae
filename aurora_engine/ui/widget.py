# aurora_engine/ui/widget.py

from typing import Optional, List
import numpy as np
from aurora_engine.core.logging import get_logger

logger = get_logger()

class Widget:
    """
    Base UI widget class.
    All UI elements inherit from this.
    """

    def __init__(self, name: str):
        self.name = name

        # Hierarchy
        self.parent: Optional[Widget] = None
        self.children: List[Widget] = []

        # Transform
        self.position = np.array([0, 0], dtype=np.float32)
        self.size = np.array([100, 100], dtype=np.float32)
        self.anchor = np.array([0.0, 0.0], dtype=np.float32)  # 0-1 range
        self.pivot = np.array([0.5, 0.5], dtype=np.float32)

        # State
        self.visible = True
        self.enabled = True
        self.focused = False

        # Events
        self.on_click = None
        self.on_hover = None
        
        # logger.debug(f"Widget '{name}' created")

    def add_child(self, child: 'Widget'):
        """Add child widget."""
        child.parent = self
        self.children.append(child)

    def remove_child(self, child: 'Widget'):
        """Remove child widget."""
        if child in self.children:
            child.parent = None
            self.children.remove(child)

    def update(self, dt: float):
        """Update widget and children."""
        if not self.enabled:
            return

        for child in self.children:
            child.update(dt)

    def render(self):
        """Render widget and children."""
        if not self.visible:
            return

        self._render_self()

        for child in self.children:
            child.render()

    def _render_self(self):
        """Override to render widget content."""
        pass

    def get_screen_position(self) -> np.ndarray:
        """Get position in screen space."""
        if self.parent:
            parent_pos = self.parent.get_screen_position()
            parent_size = self.parent.size

            # Apply anchor
            anchored_pos = parent_pos + self.anchor * parent_size

            return anchored_pos + self.position
        else:
            return self.position.copy()


class Panel(Widget):
    """Rectangular panel widget."""

    def __init__(self, name: str):
        super().__init__(name)

        self.background_color = (0.2, 0.2, 0.2, 0.9)
        self.border_color = (0.5, 0.5, 0.5, 1.0)
        self.border_width = 2


class Label(Widget):
    """Text label widget."""

    def __init__(self, name: str, text: str = ""):
        super().__init__(name)

        self.text = text
        self.font_size = 16
        self.color = (1.0, 1.0, 1.0, 1.0)
        self.alignment = "left" # Default to left for debug text

        # Backend
        self._node_path = None
        self._text_node = None
        self._loaded = False

    def _render_self(self):
        if not self._loaded:
            self._load_resources()

        if self._node_path:
            if not self.visible:
                self._node_path.hide()
                return
            self._node_path.show()

            # Update text if changed
            if self._text_node.getText() != self.text:
                self._text_node.setText(self.text)

            # Update color
            self._text_node.setTextColor(self.color)

            # Position
            pos = self.get_screen_position()
            # pixel2d: Y is Z-down.
            self._node_path.setPos(pos[0], 0, -pos[1])

            # Scale (Font Size)
            self._node_path.setScale(self.font_size)

    def _load_resources(self):
        import builtins
        from panda3d.core import TextNode, NodePath, TransparencyAttrib

        if hasattr(builtins, 'base'):
            self._text_node = TextNode(self.name)
            self._text_node.setText(self.text)
            self._text_node.setTextColor(self.color)

            # Alignment
            if self.alignment == "left":
                self._text_node.setAlign(TextNode.ALeft)
            elif self.alignment == "center":
                self._text_node.setAlign(TextNode.ACenter)
            elif self.alignment == "right":
                self._text_node.setAlign(TextNode.ARight)

            self._node_path = NodePath(self._text_node)
            self._node_path.reparentTo(builtins.base.pixel2d)
            self._node_path.setTransparency(TransparencyAttrib.MAlpha)

            self._loaded = True

    def destroy(self):
        if self._node_path:
            self._node_path.removeNode()
            self._node_path = None
        self._loaded = False


class Button(Widget):
    """Clickable button widget."""

    def __init__(self, name: str, text: str = ""):
        super().__init__(name)

        self.text = text
        self.normal_color = (0.3, 0.3, 0.3, 1.0)
        self.hover_color = (0.4, 0.4, 0.4, 1.0)
        self.pressed_color = (0.2, 0.2, 0.2, 1.0)

        self.hovered = False
        self.pressed = False
