# aurora_engine/world/chunk.py

import numpy as np
from typing import List, Set
from aurora_engine.ecs.entity import Entity
from aurora_engine.database.db_manager import DatabaseManager
from aurora_engine.scene.scene_loader import SceneLoader


class Chunk:
    """
    World chunk.
    Represents a portion of the game world.
    """

    def __init__(self, x: int, y: int, z: int, size: float = 100.0, db_manager: DatabaseManager = None):
        self.x = x
        self.y = y
        self.z = z
        self.size = size
        self.db_manager = db_manager

        # Entities in this chunk
        self.entities: Set[Entity] = set()

        # Load state
        self.loaded = False
        self.loading = False

        # Neighbors (for seamless transitions)
        self.neighbors: List['Chunk'] = []

    def get_world_position(self) -> np.ndarray:
        """Get chunk center in world space."""
        return np.array([
            self.x * self.size,
            self.y * self.size,
            self.z * self.size
        ], dtype=np.float32)

    def add_entity(self, entity: Entity):
        """Add entity to chunk."""
        self.entities.add(entity)

    def remove_entity(self, entity: Entity):
        """Remove entity from chunk."""
        if entity in self.entities:
            self.entities.discard(entity)

    def contains_point(self, point: np.ndarray) -> bool:
        """Check if point is inside chunk bounds."""
        chunk_pos = self.get_world_position()
        half_size = self.size / 2.0

        return (abs(point[0] - chunk_pos[0]) <= half_size and
                abs(point[1] - chunk_pos[1]) <= half_size and
                abs(point[2] - chunk_pos[2]) <= half_size)

    def load(self):
        """Load chunk data."""
        if self.loaded or self.loading:
            return

        self.loading = True

        # Load chunk data from database if available
        if self.db_manager:
            # Placeholder for DB loading logic
            # data = self.db_manager.fetch_one("SELECT data FROM chunks WHERE x=? AND y=? AND z=?", (self.x, self.y, self.z))
            # if data:
            #     SceneLoader.load_chunk_data(self, data['data'])
            pass
        
        # Procedural generation or default content if not in DB
        # For now, we just mark it as loaded.
        
        self.loaded = True
        self.loading = False

    def unload(self):
        """Unload chunk data."""
        if not self.loaded:
            return

        # Save chunk state to database
        if self.db_manager:
            # Placeholder for DB saving logic
            # data = SceneLoader.serialize_chunk(self)
            # self.db_manager.execute("INSERT OR REPLACE INTO chunks ...", ...)
            pass

        # Destroy entities
        # We need to be careful not to destroy persistent entities like the player
        # if they just moved out of the chunk.
        # Usually, entities are managed by the World, and the Chunk just references them.
        # But if we are unloading, we should remove non-persistent entities from the World.
        
        # For this implementation, we'll assume entities in the chunk list belong to the chunk
        # and should be removed from the main World entity list if we had access to it.
        # Since we don't have reference to World here, we just clear the list.
        # The World system needs to handle the actual destruction.
        
        self.entities.clear()
        self.loaded = False
