# aurora_engine/world/spatial_hash.py

from typing import Dict, List, Set
import numpy as np
from aurora_engine.ecs.entity import Entity


class SpatialHash:
    """
    Spatial hash for fast spatial queries.
    Used for finding entities near a point.
    """

    def __init__(self, cell_size: float = 10.0):
        self.cell_size = cell_size

        # Hash grid: (x, y, z) -> set of entities
        self.grid: Dict[tuple, Set[Entity]] = {}

        # Entity positions (for updates)
        self.entity_positions: Dict[Entity, np.ndarray] = {}

    def insert(self, entity: Entity, position: np.ndarray):
        """Insert entity at position."""
        cell = self._position_to_cell(position)

        if cell not in self.grid:
            self.grid[cell] = set()

        self.grid[cell].add(entity)
        self.entity_positions[entity] = position.copy()

    def remove(self, entity: Entity):
        """Remove entity from spatial hash."""
        if entity not in self.entity_positions:
            return

        position = self.entity_positions[entity]
        cell = self._position_to_cell(position)

        if cell in self.grid:
            self.grid[cell].discard(entity)
            if not self.grid[cell]:
                del self.grid[cell]

        del self.entity_positions[entity]

    def update(self, entity: Entity, new_position: np.ndarray):
        """Update entity position."""
        if entity in self.entity_positions:
            old_cell = self._position_to_cell(self.entity_positions[entity])
            new_cell = self._position_to_cell(new_position)

            # If cell changed, move entity
            if old_cell != new_cell:
                if old_cell in self.grid:
                    self.grid[old_cell].discard(entity)
                    if not self.grid[old_cell]:
                        del self.grid[old_cell]

                if new_cell not in self.grid:
                    self.grid[new_cell] = set()

                self.grid[new_cell].add(entity)

            self.entity_positions[entity] = new_position.copy()
        else:
            self.insert(entity, new_position)

    def query_radius(self, position: np.ndarray, radius: float) -> List[Entity]:
        """Find all entities within radius of position."""
        # Get cells to check
        cells_to_check = self._get_cells_in_radius(position, radius)

        # Collect entities
        candidates = set()
        for cell in cells_to_check:
            if cell in self.grid:
                candidates.update(self.grid[cell])

        # Filter by exact distance
        results = []
        for entity in candidates:
            entity_pos = self.entity_positions[entity]
            distance = np.linalg.norm(position - entity_pos)
            if distance <= radius:
                results.append(entity)

        return results

    def _position_to_cell(self, position: np.ndarray) -> tuple:
        """Convert world position to cell coordinates."""
        return (
            int(np.floor(position[0] / self.cell_size)),
            int(np.floor(position[1] / self.cell_size)),
            int(np.floor(position[2] / self.cell_size))
        )

    def _get_cells_in_radius(self, position: np.ndarray, radius: float) -> List[tuple]:
        """Get all cells that could contain entities within radius."""
        cell_radius = int(np.ceil(radius / self.cell_size))
        center_cell = self._position_to_cell(position)

        cells = []
        for dx in range(-cell_radius, cell_radius + 1):
            for dy in range(-cell_radius, cell_radius + 1):
                for dz in range(-cell_radius, cell_radius + 1):
                    cells.append((
                        center_cell[0] + dx,
                        center_cell[1] + dy,
                        center_cell[2] + dz
                    ))

        return cells
