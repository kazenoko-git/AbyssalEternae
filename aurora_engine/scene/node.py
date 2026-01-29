# aurora_engine/scene/node.py

from typing import List, Optional, Dict, Any
from aurora_engine.scene.transform import Transform
from aurora_engine.core.logging import get_logger

logger = get_logger()

class SceneNode:
    """
    Base class for scene graph nodes.
    Wraps an entity or a logical grouping in the scene hierarchy.
    """

    def __init__(self, name: str = "Node"):
        self.name = name
        self.transform = Transform()
        self.parent: Optional['SceneNode'] = None
        self.children: List['SceneNode'] = []
        
        # Optional: Link to ECS Entity if this node represents one
        self.entity_id: Optional[int] = None
        
        # Metadata
        self.tags: List[str] = []
        self.active = True
        # logger.debug(f"SceneNode '{name}' created")

    def add_child(self, child: 'SceneNode'):
        """Add a child node."""
        if child.parent:
            child.parent.remove_child(child)
            
        child.parent = self
        self.children.append(child)
        
        # Link transforms
        child.transform.set_parent(self.transform)
        # logger.debug(f"Added child '{child.name}' to '{self.name}'")

    def remove_child(self, child: 'SceneNode'):
        """Remove a child node."""
        if child in self.children:
            self.children.remove(child)
            child.parent = None
            child.transform.set_parent(None)
            # logger.debug(f"Removed child '{child.name}' from '{self.name}'")

    def find_child(self, name: str, recursive: bool = True) -> Optional['SceneNode']:
        """Find a child by name."""
        for child in self.children:
            if child.name == name:
                return child
            
            if recursive:
                result = child.find_child(name, recursive)
                if result:
                    return result
        return None

    def traverse(self, callback):
        """Traverse the hierarchy (DFS)."""
        callback(self)
        for child in self.children:
            child.traverse(callback)
