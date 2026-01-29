# aurora_engine/ui/layout.py

from enum import Enum
from typing import List, Tuple
import numpy as np
from aurora_engine.ui.widget import Widget
from aurora_engine.core.logging import get_logger

logger = get_logger()

class LayoutType(Enum):
    VERTICAL = 0
    HORIZONTAL = 1
    GRID = 2


class Layout:
    """
    Base class for UI layouts.
    Arranges child widgets automatically.
    """

    def __init__(self):
        self.padding = (0, 0, 0, 0)  # Left, Top, Right, Bottom
        self.spacing = 5.0

    def apply(self, container: Widget, children: List[Widget]):
        """Apply layout to children."""
        pass


class LinearLayout(Layout):
    """
    Arranges widgets in a line (vertical or horizontal).
    """

    def __init__(self, orientation: LayoutType = LayoutType.VERTICAL):
        super().__init__()
        self.orientation = orientation
        self.alignment = "start"  # start, center, end

    def apply(self, container: Widget, children: List[Widget]):
        start_x = container.position[0] + self.padding[0]
        start_y = container.position[1] + self.padding[1]
        
        current_x = start_x
        current_y = start_y
        
        container_width = container.size[0]
        container_height = container.size[1]
        
        # Calculate total content size for alignment
        total_width = 0
        total_height = 0
        
        for child in children:
            if not child.visible:
                continue
            total_width += child.size[0]
            total_height += child.size[1]
            
        # Add spacing
        visible_children = [c for c in children if c.visible]
        if len(visible_children) > 1:
            spacing_total = (len(visible_children) - 1) * self.spacing
            if self.orientation == LayoutType.HORIZONTAL:
                total_width += spacing_total
            else:
                total_height += spacing_total

        # Adjust start position based on alignment
        if self.alignment == "center":
            if self.orientation == LayoutType.HORIZONTAL:
                current_x += (container_width - total_width) / 2
            else:
                current_y += (container_height - total_height) / 2
        elif self.alignment == "end":
            if self.orientation == LayoutType.HORIZONTAL:
                current_x += (container_width - total_width)
            else:
                current_y += (container_height - total_height)

        # Position children
        for child in children:
            if not child.visible:
                continue
                
            child.position = np.array([current_x, current_y], dtype=np.float32)
            
            if self.orientation == LayoutType.HORIZONTAL:
                current_x += child.size[0] + self.spacing
            else:
                current_y += child.size[1] + self.spacing


class GridLayout(Layout):
    """
    Arranges widgets in a grid.
    """

    def __init__(self, columns: int = 2):
        super().__init__()
        self.columns = columns
        self.row_spacing = 5.0
        self.col_spacing = 5.0

    def apply(self, container: Widget, children: List[Widget]):
        start_x = container.position[0] + self.padding[0]
        start_y = container.position[1] + self.padding[1]
        
        current_col = 0
        current_row = 0
        
        # Determine cell size (assuming uniform grid or max size)
        # For simple grid, we might assume fixed cell size or max of children
        max_w = 0
        max_h = 0
        for child in children:
            if child.visible:
                max_w = max(max_w, child.size[0])
                max_h = max(max_h, child.size[1])
                
        for child in children:
            if not child.visible:
                continue
                
            x = start_x + current_col * (max_w + self.col_spacing)
            y = start_y + current_row * (max_h + self.row_spacing)
            
            child.position = np.array([x, y], dtype=np.float32)
            
            current_col += 1
            if current_col >= self.columns:
                current_col = 0
                current_row += 1
