# aurora_engine/resources/prefab.py

from typing import Dict, Any, List
from aurora_engine.ecs.entity import Entity
from aurora_engine.ecs.component import Component
import json
from aurora_engine.core.logging import get_logger

logger = get_logger()

class Prefab:
    """
    Prefab (template) for creating entities.
    Stores component data in serialized form.
    """

    def __init__(self, name: str):
        self.name = name
        self.components: List[Dict[str, Any]] = []

    def add_component_data(self, component_type: str, data: Dict[str, Any]):
        """Add component template."""
        self.components.append({
            'type': component_type,
            'data': data
        })

    def instantiate(self, world) -> Entity:
        """Create entity from prefab."""
        entity = world.create_entity()

        for component_data in self.components:
            # Deserialize and attach component
            try:
                component = self._deserialize_component(component_data)
                entity.add_component(component)
            except Exception as e:
                logger.error(f"Failed to instantiate component {component_data.get('type')}: {e}")

        return entity

    def _deserialize_component(self, data: Dict) -> Component:
        """Reconstruct component from data."""
        from aurora_engine.ecs.registry import ComponentRegistry

        component_type = data['type']
        component_data = data['data']

        # Get component class from registry
        component_class = ComponentRegistry.get(component_type)
        if not component_class:
            raise ValueError(f"Unknown component type: {component_type}")

        # Create component instance
        # Some components might require arguments in __init__
        # We assume they have default constructors or we handle specific ones
        try:
            component = component_class()
        except TypeError:
            # Fallback for components requiring args (e.g. Collider)
            # This is a simplification. A proper serialization system would handle this better.
            # For now, we try to pass data as kwargs if possible, or just fail.
            # Let's try to inspect the init? No, too complex.
            # Let's assume we can init empty and set properties.
            # If not, we need a factory.
            raise ValueError(f"Component {component_type} requires arguments for initialization.")

        # Set component properties from data
        for key, value in component_data.items():
            if hasattr(component, key):
                setattr(component, key, value)

        return component

    def save(self, filepath: str):
        """Save prefab to file."""
        data = {
            'name': self.name,
            'components': self.components
        }

        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved prefab '{self.name}' to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save prefab '{self.name}' to {filepath}: {e}")

    @staticmethod
    def load(filepath: str) -> 'Prefab':
        """Load prefab from file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            prefab = Prefab(data['name'])
            prefab.components = data['components']
            logger.info(f"Loaded prefab '{prefab.name}' from {filepath}")
            return prefab
        except Exception as e:
            logger.error(f"Failed to load prefab from {filepath}: {e}")
            return Prefab("Error")
