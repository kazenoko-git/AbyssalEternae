# game/main.py

import os
import json
import numpy as np

from aurora_engine.core.application import Application
from aurora_engine.scene.transform import Transform
from aurora_engine.core.logging import get_logger
from aurora_engine.database.db_manager import DatabaseManager
from aurora_engine.database.schema import DatabaseSchema

from game.systems.dialogue_system import DialogueSystem
from game.systems.world_generator import WorldGenerator
from game.ai.ai_generator import AIContentGenerator

from game.managers.world_manager import WorldManager
from game.managers.player_manager import PlayerManager
from game.managers.ai_manager import AIManager
from game.managers.debug_manager import DebugManager
from game.managers.game_ui_manager import GameUIManager
from game.managers.environment_manager import EnvironmentManager

logger = get_logger()

class AbyssalEternae(Application):
    """
    The Main RPG Game Application.
    """

    def initialize_game(self):
        """Game-specific initialization."""
        logger.info("Initializing Abyssal Eternae Game...")
        
        # Initialize Database
        self._setup_database()
        
        # Initialize AI & World Gen
        self.ai_generator = AIContentGenerator(self.db_manager)
        self.world_generator = WorldGenerator(self.db_manager, self.ai_generator)
        
        # Initialize Managers
        self.world_manager = WorldManager(self.world, self.db_manager, self.world_generator)
        self.player_manager = PlayerManager(self.world, self.input, self.physics, self.renderer)
        self.ai_manager = AIManager(self.db_manager, self.ai_generator)
        self.debug_manager = DebugManager(self.renderer, self.input, self.physics, self.ui)
        self.game_ui_manager = GameUIManager(self.ui, self.config)
        self.environment_manager = EnvironmentManager(self.world, self.renderer, self.world_manager)
        
        # Setup World
        self.world_manager.initialize_world()
        
        # Create Player
        # Initial position will be adjusted after terrain load
        initial_pos = np.array([0, 0, 10.0], dtype=np.float32)
        self.player = self.player_manager.create_player(initial_pos)
        
        # Load Initial Area
        self.world_manager.load_initial_area(initial_pos)
        
        # Adjust Player Height
        h = self.world_manager.get_ground_height(0, 0)
        self.player.get_component(Transform).set_world_position(np.array([0, 0, h + 5.0], dtype=np.float32))

        # Setup Environment (Day/Night, Fog, etc)
        self.environment_manager.setup(self.player.get_component(Transform))
        
        # Setup UI
        self.game_ui_manager.setup_ui()
        
        # Add Game Systems
        dialogue_system = DialogueSystem(self.ui)
        dialogue_system.ai_manager = self.ai_manager
        self.world.add_system(dialogue_system)

    def _setup_database(self):
        """Initialize database connection."""
        db_config = self.config.get('database', {})
        if not db_config:
             db_config = {
                'host': 'localhost',
                'user': 'root',
                'password': '',
                'database': 'abyssal_eternae_db',
                'port': 3306
            }
            
        self.db_manager = DatabaseManager(db_config)
        self.db_manager.connect()
        DatabaseSchema.create_tables(self.db_manager)

    def update(self, dt: float, alpha: float):
        """Override update to update managers."""
        super().update(dt, alpha)
        
        # Update Managers
        player_pos = self.player_manager.get_position()
        cam_transform = self.player_manager.get_camera_transform()
        
        if cam_transform:
            self.world_manager.update_chunks(dt, player_pos, cam_transform)
        
        self.player_manager.update(dt, alpha)
        self.ai_manager.update_emotions(dt)
        self.debug_manager.update(dt, player_pos)
        
        # Toggle mouse lock with Escape
        if self.input.is_key_down('escape'):
            self.input.set_mouse_lock(False)
        elif self.input.is_key_down('mouse1') and not self.input.mouse_locked:
            self.input.set_mouse_lock(True)
        
    def late_update(self, dt: float, alpha: float):
        """Update camera after physics."""
        # Player manager handles camera update in its update()
        pass

    def shutdown(self):
        """Cleanup."""
        super().shutdown()
        if hasattr(self, 'db_manager'):
            self.db_manager.disconnect()


if __name__ == "__main__":
    config_path = "config.json"
    if not os.path.exists(config_path):
        config_data = {
            'rendering': {
                'width': 1280,
                'height': 720,
                'title': 'Abyssal Eternae',
            },
            'database': {
                'host': 'localhost',
                'user': 'root',
                'password': 'Yippee_12345',
                'database': 'abyssal_eternae_db',
                'port': 3306
            }
        }

        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)

    game = AbyssalEternae(config_path)
    game.run()
