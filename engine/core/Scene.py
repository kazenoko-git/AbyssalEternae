from engine.ecs.World import World


class Scene:
    def __init__(self, renderRoot):
        self.World = World()
        self.RenderRoot = renderRoot

    def Load(self):
        pass

    def Update(self):
        self.World.Update()

    def FixedUpdate(self):
        self.World.FixedUpdate()

    def Unload(self):
        pass
