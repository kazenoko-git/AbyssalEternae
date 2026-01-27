# aurora_engine/ecs/component.py

class Component:
    """
    Base class for all components.
    Components are pure data containers.
    """

    def __init__(self):
        self.entity = None  # Back-reference to owner
        self.enabled = True