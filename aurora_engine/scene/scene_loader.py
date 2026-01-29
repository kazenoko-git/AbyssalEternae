# aurora_engine/scene/scene_loader.py

from typing import List, Dict, Any
import numpy as np
from aurora_engine.ecs.world import World
from aurora_engine.resources.prefab import Prefab
import json
from aurora_engine.core.logging import get_logger

logger = get_logger()

class Scene:
    """
    Scene definition.
    Contains entity instances and scene settings.
    """

    def __init__(self, name: str):
        self.name = name
        self.entities: List[Dict[str, Any]] = []
        self.settings: Dict[str, Any] = {
            'ambient_light': [0.2, 0.2, 0.2],
            'fog_enabled': False,
            'skybox': None,
        }

    def add_entity_instance(self, prefab_path: str, transform_data: Dict):
        """Add entity instance to scene."""
        self.entities.append({
            'prefab': prefab_path,
            'transform': transform_data
        })

    def save(self, filepath: str):
        """Save scene to file."""
        data = {
            'name': self.name,
            'settings': self.settings,
            'entities': self.entities
        }

        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved scene '{self.name}' to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save scene '{self.name}' to {filepath}: {e}")

    @staticmethod
    def load(filepath: str) -> 'Scene':
        """Load scene from file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            scene = Scene(data['name'])
            scene.settings = data['settings']
            scene.entities = data['entities']
            logger.info(f"Loaded scene '{scene.name}' from {filepath}")
            return scene
        except Exception as e:
            logger.error(f"Failed to load scene from {filepath}: {e}")
            return Scene("Empty")


class SceneLoader:
    """
    Loads scenes into the ECS world.
    """

    def __init__(self, world: World):
        self.world = world
        self.current_scene: Scene = None

    def load_scene(self, scene: Scene):
        """Load a scene into the world."""
        logger.info(f"Loading scene: {scene.name}")
        # Clear current scene
        if self.current_scene:
            self.unload_current_scene()

        # Apply scene settings
        self._apply_scene_settings(scene.settings)

        # Instantiate all entities
        for entity_data in scene.entities:
            self._instantiate_entity(entity_data)

        self.current_scene = scene
        logger.info(f"Scene '{scene.name}' loaded successfully")

    def unload_current_scene(self):
        """Unload current scene."""
        if not self.current_scene:
            return
            
        logger.info(f"Unloading scene: {self.current_scene.name}")
        # Destroy all entities
        for entity in self.world.entities[:]:
            self.world.destroy_entity(entity)

        self.current_scene = None

    def _instantiate_entity(self, entity_data: Dict):
        """Create entity from scene data."""
        try:
            # Load prefab
            prefab = Prefab.load(entity_data['prefab'])

            # Instantiate
            entity = prefab.instantiate(self.world)

            # Apply transform
            from aurora_engine.scene.transform import Transform
            transform = entity.get_component(Transform)
            if transform and 'transform' in entity_data:
                trans_data = entity_data['transform']

                if 'position' in trans_data:
                    transform.set_local_position(np.array(trans_data['position'], dtype=np.float32))
                if 'rotation' in trans_data:
                    transform.local_rotation = np.array(trans_data['rotation'], dtype=np.float32)
                if 'scale' in trans_data:
                    transform.local_scale = np.array(trans_data['scale'], dtype=np.float32)

            return entity
        except Exception as e:
            logger.error(f"Failed to instantiate entity from prefab {entity_data.get('prefab')}: {e}")
            return None

    def _apply_scene_settings(self, settings: Dict):
        """Apply scene-level settings."""
        # TODO: Set ambient light
        # TODO: Enable/disable fog
        # TODO: Load skybox
        pass
