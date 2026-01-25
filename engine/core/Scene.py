from engine.ecs.World import World


class Scene:
    def __init__(self, engine):
        self.Engine = engine
        self.World = World()
        self.RenderRoot = engine.render
        self.Input = None

    def Load(self):
        pass

    def Update(self):
        self.World.Update()

    def FixedUpdate(self):
        self.World.FixedUpdate()

    def Unload(self):
        pass
