from engine.ecs.System import System
from engine.ecs.components.Transform import Transform
from engine.ecs.components.MeshRenderer import MeshRenderer
from engine.rendering.MeshLibrary import MeshLibrary


class RenderSystem(System):
    def __init__(self, renderRoot, loader):
        self.RenderRoot = renderRoot
        self.Loader = loader
        self._Nodes = {}  # entityId -> NodePath

    def Update(self, world):
        for entityId in world.Query(Transform, MeshRenderer):
            transform = world._Components[Transform][entityId]
            mesh = world._Components[MeshRenderer][entityId]

            if entityId not in self._Nodes:
                node = MeshLibrary.Load(mesh.MeshName, self.Loader)
                node.reparentTo(self.RenderRoot)
                node.setColor(*mesh.Color)
                node.setTwoSided(True)

                self._Nodes[entityId] = node

            node = self._Nodes[entityId]
            node.setTwoSided(True)
            node.setPos(*transform.WorldPosition)
            node.setHpr(*transform.WorldRotation)
            node.setScale(*transform.WorldScale)

    def FixedUpdate(self, world):
        pass
