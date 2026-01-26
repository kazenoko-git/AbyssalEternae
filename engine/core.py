from panda3d.core import NodePath


# ==================================================================================
# 🧠 UNITY CORE ARCHITECTURE
# ==================================================================================

class Component:
    def __init__(self):
        self.gameObject = None
        self.transform = None

    def awake(self): pass

    def start(self): pass

    def update(self, dt): pass

    def on_gui(self): pass


class GameObject:
    def __init__(self, name, model="models/box", pos=(0, 0, 0), scale=1.0, parent=None):
        self.name = name
        self.components = []
        self.active = True

        # Physics / Visual Node
        # We assume 'base' is available globally (standard Panda3D behavior)
        if model:
            try:
                self.node = base.loader.loadModel(model)
            except:
                print(f"⚠️ Could not load model {model}, using smiley.")
                self.node = base.loader.loadModel("models/smiley")
        else:
            self.node = NodePath(name)

        self.node.setPos(pos)
        self.node.setScale(scale)
        self.node.setColorScale(0.8, 0.8, 0.8, 1)  # Default grey

        if parent:
            self.node.reparentTo(parent)
        else:
            self.node.reparentTo(base.render)

        # Register to Scene via the global engine reference
        if hasattr(base, 'engine'):
            base.engine.register_object(self)

    def add_component(self, component_cls):
        comp = component_cls()
        comp.gameObject = self
        comp.transform = self.node
        self.components.append(comp)
        comp.awake()
        return comp

    def get_component(self, component_cls):
        for c in self.components:
            if isinstance(c, component_cls): return c
        return None

    def _start(self):
        for c in self.components: c.start()

    def _update(self, dt):
        if not self.active: return
        for c in self.components: c.update(dt)