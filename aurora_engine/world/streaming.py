# aurora_engine/world/streaming.py

import numpy as np
from typing import Dict, Tuple, List
from aurora_engine.world.chunk import Chunk
from aurora_engine.scene.transform import Transform
from aurora_engine.database.db_manager import DatabaseManager
from aurora_engine.core.logging import get_logger

logger = get_logger()

class StreamingManager:
    """
    Manages world streaming based on player/camera position.
    Loads/unloads chunks dynamically.
    """

    def __init__(self, chunk_size: float = 100.0, db_manager: DatabaseManager = None):
        self.chunk_size = chunk_size
        self.db_manager = db_manager

        # All chunks (loaded and unloaded)
        self.chunks: Dict[Tuple[int, int, int], Chunk] = {}

        # Streaming settings
        self.load_radius = 3  # Chunks to load around player
        self.unload_radius = 5  # Chunks to unload beyond this

        # Streaming focus (usually player position)
        self.focus_position = np.array([0.0, 0.0, 0.0], dtype=np.float32)

        logger.info(f"StreamingManager initialized with chunk_size={chunk_size}")

    def set_focus(self, position: np.ndarray):
        """Set streaming focus position (e.g., player location)."""
        self.focus_position = position.copy()

    def update(self):
        """Update chunk streaming."""
        # Get chunk coordinates at focus
        focus_chunk = self._world_to_chunk(self.focus_position)

        # Determine which chunks should be loaded
        chunks_to_load = self._get_chunks_in_radius(focus_chunk, self.load_radius)
        chunks_to_unload = []

        # Load needed chunks
        for chunk_coords in chunks_to_load:
            chunk = self._get_or_create_chunk(chunk_coords)
            if not chunk.loaded and not chunk.loading:
                chunk.load()

        # Find chunks to unload
        for chunk_coords, chunk in self.chunks.items():
            if chunk.loaded:
                distance = self._chunk_distance(chunk_coords, focus_chunk)
                if distance > self.unload_radius:
                    chunks_to_unload.append(chunk)

        # Unload distant chunks
        for chunk in chunks_to_unload:
            chunk.unload()

    def _world_to_chunk(self, position: np.ndarray) -> Tuple[int, int, int]:
        """Convert world position to chunk coordinates."""
        return (
            int(np.floor(position[0] / self.chunk_size)),
            int(np.floor(position[1] / self.chunk_size)),
            int(np.floor(position[2] / self.chunk_size))
        )

    def _get_chunks_in_radius(self, center: Tuple[int, int, int], radius: int) -> List[Tuple[int, int, int]]:
        """Get all chunk coordinates within radius."""
        chunks = []
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                for dz in range(-1, 2):  # Limited vertical range
                    chunks.append((
                        center[0] + dx,
                        center[1] + dy,
                        center[2] + dz
                    ))
        return chunks

    def _chunk_distance(self, a: Tuple[int, int, int], b: Tuple[int, int, int]) -> float:
        """Calculate distance between chunk coordinates."""
        return np.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)

    def _get_or_create_chunk(self, coords: Tuple[int, int, int]) -> Chunk:
        """Get existing chunk or create new one."""
        if coords not in self.chunks:
            self.chunks[coords] = Chunk(coords[0], coords[1], coords[2], self.chunk_size, self.db_manager)
        return self.chunks[coords]

    def get_chunk_at_position(self, position: np.ndarray) -> Chunk:
        """Get chunk containing world position."""
        chunk_coords = self._world_to_chunk(position)
        return self._get_or_create_chunk(chunk_coords)
