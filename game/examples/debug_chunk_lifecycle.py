# game/examples/debug_chunk_lifecycle.py

from aurora_engine.core.application import Application
from aurora_engine.ecs.entity import Entity
from game.systems.world_generator import WorldGenerator
from game.ai.ai_generator import AIContentGenerator
from aurora_engine.database.db_manager import DatabaseManager
from aurora_engine.database.schema import DatabaseSchema
from aurora_engine.core.logging import get_logger
import numpy as np
import time
import os
import psutil
import json

logger = get_logger()

class ChunkLifecycleTest(Application):
    """
    Debug script to verify chunk loading and unloading logic.
    """

    def initialize_game(self):
        logger.info("Initializing Lifecycle Test...")
        
        # DB Setup
        db_config = {
            'database': 'eternae_lifecycle_test.db'
        }
        self.db_manager = DatabaseManager(db_config)
        self.db_manager.connect()
        DatabaseSchema.drop_tables(self.db_manager)
        DatabaseSchema.create_tables(self.db_manager)
        
        self.ai_generator = AIContentGenerator(self.db_manager)
        self.world_generator = WorldGenerator(self.db_manager, self.ai_generator)
        
        # Virtual Camera
        self.cam_pos = np.array([0.0, 0.0, 0.0])
        self.cam_speed = 10.0 # Fast movement
        
        self.loaded_chunks = {}
        self.load_radius = 2
        self.unload_radius = 3
        
        self.world_generator.get_or_create_dimension("dim_debug", 123)
        
        # Disable rendering for speed/focus (optional, but we want to test node removal)
        # self.renderer.backend.window.setActive(False) 

    def update(self, dt: float, alpha: float):
        # Move camera forward
        self.cam_pos[1] += self.cam_speed * dt
        
        # Manage Chunks
        self._manage_chunks()
        
        # Report
        mem = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        logger.info(f"Pos: {self.cam_pos[1]:.1f} | Loaded: {len(self.loaded_chunks)} | Entities: {len(self.world.entities)} | Mem: {mem:.1f} MB")

    def _manage_chunks(self):
        chunk_x = int(self.cam_pos[0] // 100)
        chunk_y = int(self.cam_pos[1] // 100)
        
        # Load
        for dx in range(-self.load_radius, self.load_radius + 1):
            for dy in range(-self.load_radius, self.load_radius + 1):
                cx, cy = chunk_x + dx, chunk_y + dy
                if (cx, cy) not in self.loaded_chunks:
                    self._load_chunk(cx, cy)
                    
        # Unload
        to_remove = []
        for coords in self.loaded_chunks:
            dist = np.sqrt((coords[0]*100 - self.cam_pos[0])**2 + (coords[1]*100 - self.cam_pos[1])**2)
            if dist > self.unload_radius * 100:
                to_remove.append(coords)
                
        for coords in to_remove:
            self._unload_chunk(coords)

    def _load_chunk(self, x, y):
        # Generate data (sync for this test to isolate leaks from async issues)
        region = self.world_generator.generate_region("dim_debug", x, y)
        
        # Create dummy entities to simulate load
        entities = []
        # 1 Terrain + 10 Props
        for _ in range(11):
            e = self.world.create_entity()
            # Add a dummy component that prints on destroy?
            # e.add_component(DebugComponent())
            entities.append(e)
            
        self.loaded_chunks[(x, y)] = entities

    def _unload_chunk(self, coords):
        entities = self.loaded_chunks[coords]
        for e in entities:
            self.world.destroy_entity(e)
        del self.loaded_chunks[coords]

    def shutdown(self):
        super().shutdown()
        self.db_manager.disconnect()

if __name__ == "__main__":
    # Minimal config
    config = {
        'rendering': {'width': 800, 'height': 600, 'title': 'Lifecycle Test'},
        'database': {'database': 'eternae_lifecycle_test.db'}
    }
    with open("debug_config.json", "w") as f:
        json.dump(config, f)
        
    app = ChunkLifecycleTest("debug_config.json")
    app.run()
