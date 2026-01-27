# aurora_engine/scene/scene.py

from typing import List, Dict, Any, Optional
from aurora_engine.scene.node import SceneNode
from aurora_engine.ecs.world import World


class Scene:
    """
    Runtime representation of a scene.
    Manages the scene graph and integration with ECS.
    """

    def __init__(self, name: str):
        self.name = name
        self.root = SceneNode("Root")
        self.world: Optional[World] = None
        
        # Scene-specific settings
        self.ambient_color = (0.2, 0.2, 0.2, 1.0)
        self.fog_enabled = False
        self.fog_color = (0.5, 0.5, 0.5, 1.0)
        self.fog_density = 0.01

    def update(self, dt: float):
        """Update scene logic."""
        # Update scene graph transforms if needed
        # (Transforms usually update lazily, but we might have scene-specific logic)
        pass

    def add_node(self, node: SceneNode, parent: SceneNode = None):
        """Add a node to the scene."""
        if parent is None:
            parent = self.root
        parent.add_child(node)

    def remove_node(self, node: SceneNode):
        """Remove a node from the scene."""
        if node.parent:
            node.parent.remove_child(node)

    def get_node_by_name(self, name: str) -> Optional[SceneNode]:
        """Find a node by name."""
        return self.root.find_child(name)
