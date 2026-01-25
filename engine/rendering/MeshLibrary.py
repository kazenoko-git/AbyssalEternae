from panda3d.core import CardMaker


class MeshLibrary:
    @staticmethod
    def Load(meshName, loader):
        if meshName == "plane":
            cm = CardMaker("plane")
            cm.setFrame(-5, 5, -5, 5)
            node = cm.generate()
            node.setHpr(0, -90, 0)
            return node

        elif meshName == "cube":
            return loader.loadModel("models/box")

        else:
            raise ValueError(f"Unknown mesh: {meshName}")
