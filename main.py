from panda3d.core import DirectionalLight, LVector3
from engine.App import EngineApp
from engine.Terrain import CreateFlatTerrain

app = EngineApp()

terrainNode = CreateFlatTerrain()
terrain = app.render.attachNewNode(terrainNode)
terrain.setColor(0.2, 0.7, 0.2, 1)

# Camera
app.camera.setPos(5, -20, 10)
app.camera.lookAt(5, 5, 0)

# Light (EXPLICIT)
light = DirectionalLight("sun")
lightNP = app.render.attachNewNode(light)
lightNP.setHpr(-45, -60, 0)
app.render.setLight(lightNP)

app.run()
