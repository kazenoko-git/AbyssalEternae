# aurora_engine/ecs/registry.py

from typing import Dict, Type
from aurora_engine.ecs.component import Component
from aurora_engine.ecs.system import System


class ComponentRegistry:
    """
    Component type registry.
    Maps component names to classes for serialization.
    """

    _components: Dict[str, Type[Component]] = {}

    @classmethod
    def register(cls, name: str, component_class: Type[Component]):
        """Register a component type."""
        cls._components[name] = component_class

    @classmethod
    def get(cls, name: str) -> Type[Component]:
        """Get component class by name."""
        return cls._components.get(name)

    @classmethod
    def get_all(cls) -> Dict[str, Type[Component]]:
        """Get all registered components."""
        return cls._components.copy()


class SystemRegistry:
    """
    System type registry.
    Maps system names to classes.
    """

    _systems: Dict[str, Type[System]] = {}

    @classmethod
    def register(cls, name: str, system_class: Type[System]):
        """Register a system type."""
        cls._systems[name] = system_class

    @classmethod
    def get(cls, name: str) -> Type[System]:
        """Get system class by name."""
        return cls._systems.get(name)


# Auto-registration decorator
def register_component(name: str):
    """Decorator to auto-register components."""

    def decorator(cls):
        ComponentRegistry.register(name, cls)
        return cls

    return decorator


def register_system(name: str):
    """Decorator to auto-register systems."""

    def decorator(cls):
        SystemRegistry.register(name, cls)
        return cls

    return decorator