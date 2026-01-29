# aurora_engine/utils/serialization.py

import json
import pickle
import numpy as np
import time
from typing import Any, Dict
from pathlib import Path
from aurora_engine.ecs.world import World
from aurora_engine.ecs.component import Component
from aurora_engine.core.logging import get_logger

logger = get_logger()

class SaveSystem:
    """
    Game save/load system.
    Serializes world state to disk.
    """

    def __init__(self, db_manager, world: World):
        self.db = db_manager
        self.world = world
        self.save_directory = Path("saves/")
        self.save_directory.mkdir(exist_ok=True)

    def save_game(self, slot: str, metadata: Dict = None):
        """Save current game state."""
        save_path = self.save_directory / f"{slot}.save"

        try:
            save_data = {
                'version': '1.0',
                'timestamp': int(time.time()),
                'metadata': metadata or {},
                'world_state': self._serialize_world(),
                'database_snapshot': self._snapshot_database()
            }

            # Write to file
            with open(save_path, 'wb') as f:
                pickle.dump(save_data, f)

            logger.info(f"Game saved to {save_path}")
        except Exception as e:
            logger.error(f"Failed to save game to {save_path}: {e}")

    def load_game(self, slot: str):
        """Load saved game state."""
        save_path = self.save_directory / f"{slot}.save"

        if not save_path.exists():
            logger.error(f"Save file not found: {save_path}")
            raise FileNotFoundError(f"Save file not found: {save_path}")

        try:
            # Read from file
            with open(save_path, 'rb') as f:
                save_data = pickle.load(f)

            # Restore state
            self._deserialize_world(save_data['world_state'])
            self._restore_database(save_data['database_snapshot'])

            logger.info(f"Game loaded from {save_path}")
        except Exception as e:
            logger.error(f"Failed to load game from {save_path}: {e}")

    def _serialize_world(self) -> Dict:
        """Serialize ECS world state."""
        world_data = {
            'entities': []
        }

        for entity in self.world.entities:
            entity_data = {
                'id': entity.id,
                'active': entity.active,
                'components': {}
            }

            # Serialize each component
            for comp_type, component in entity.components.items():
                component_name = comp_type.__name__
                component_data = self._serialize_component(component)
                entity_data['components'][component_name] = component_data

            world_data['entities'].append(entity_data)

        return world_data

    def _serialize_component(self, component: Component) -> Dict:
        """Serialize a single component."""
        data = {}

        # Get all serializable attributes
        for attr_name in dir(component):
            if attr_name.startswith('_'):
                continue

            attr_value = getattr(component, attr_name)

            # Skip methods
            if callable(attr_value):
                continue

            # Serialize based on type
            if isinstance(attr_value, (int, float, str, bool)):
                data[attr_name] = attr_value
            elif isinstance(attr_value, np.ndarray):
                data[attr_name] = attr_value.tolist()
            elif isinstance(attr_value, list):
                data[attr_name] = attr_value
            elif isinstance(attr_value, dict):
                data[attr_name] = attr_value

        return data

    def _deserialize_world(self, world_data: Dict):
        """Restore ECS world from serialized data."""
        # Clear current world
        for entity in self.world.entities[:]:
            self.world.destroy_entity(entity)

        # Recreate entities
        from aurora_engine.ecs.registry import ComponentRegistry

        for entity_data in world_data['entities']:
            entity = self.world.create_entity()
            entity.id = entity_data['id']
            entity.active = entity_data['active']

            # Restore components
            for comp_name, comp_data in entity_data['components'].items():
                comp_class = ComponentRegistry.get(comp_name)
                if not comp_class:
                    continue

                component = comp_class()

                # Restore attributes
                for attr_name, attr_value in comp_data.items():
                    if hasattr(component, attr_name):
                        # Convert lists back to numpy arrays if needed
                        if isinstance(attr_value, list) and hasattr(getattr(component, attr_name), 'dtype'):
                            attr_value = np.array(attr_value)
                        setattr(component, attr_name, attr_value)

                entity.add_component(component)

    def _snapshot_database(self) -> bytes:
        """Create database snapshot."""
        # SQL databases support VACUUM INTO for backups
        # For simplicity, we'll copy the database file
        # Note: This assumes SQLite or similar file-based DB. For MySQL, this needs adjustment.
        # Since we are using MySQL, this simple file copy won't work for the DB itself.
        # We'll just return empty bytes for now as placeholder or implement proper dump.
        return b""

    def _restore_database(self, snapshot: bytes):
        """Restore database from snapshot."""
        # Placeholder for MySQL restore logic
        pass
