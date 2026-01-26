from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import (
    Vec4, Shader, CardMaker, AmbientLight,
    CollisionTraverser, WindowProperties, ClockObject
)
import sys

# Import our modules
import shaders
from core import GameObject
from gameplay import PlayerController, ThirdPersonCamera
from editor import EngineEditor, StorySystem, InputSystem


# ==================================================================================
# ⚙️ MAIN ENGINE CLASS
# ==================================================================================

class Engine(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        # 'base' is now available in builtins because ShowBase initialized.
        # We attach the engine instance to 'self' (which is base) so other modules can find it.
        self.engine = self

        # Get the global clock explicitly or rely on built-in
        self.globalClock = ClockObject.getGlobalClock()

        self.disableMouse()  # Disable default camera control

        # Setup Core
        self.all_objects = []
        self.editor_active = False

        # Physics
        self.cTrav = CollisionTraverser()

        # Systems
        self.input = InputSystem()
        self.story_system = StorySystem()

        # Visuals
        self.setup_lighting_and_shader()
        self.setup_scene()
        self.setup_editor()

        # Loop
        self.taskMgr.add(self.game_loop, "GameLoop")

        print("---------------------------------------")
        print(" PY-UNITY ENGINE LOADED")
        print(" [TAB] Toggle Editor/Inspector")
        print(" [WASD] Move Player")
        print("---------------------------------------")

    def register_object(self, obj):
        self.all_objects.append(obj)

    def setup_lighting_and_shader(self):
        # Apply Cel Shader to EVERYTHING
        self.cel_shader = Shader.make(Shader.SL_GLSL, shaders.CEL_VERT, shaders.CEL_FRAG)
        self.render.setShader(self.cel_shader)

        # Lights (For standard materials fallback)
        alight = AmbientLight('alight')
        alight.setColor(Vec4(0.2, 0.2, 0.2, 1))
        self.render.setLight(self.render.attachNewNode(alight))

    def setup_scene(self):
        # Ground
        cm = CardMaker('ground')
        cm.setFrame(-50, 50, -50, 50)
        ground = self.render.attachNewNode(cm.generate())
        ground.setP(-90)
        ground.setColorScale(0.2, 0.5, 0.2, 1)  # Green

        # Player
        self.player = GameObject("Hero", "models/panda", pos=(0, 0, 0), scale=0.5)
        self.player.add_component(PlayerController)
        self.player.add_component(ThirdPersonCamera)

        # Enemies / Props
        enemy = GameObject("Enemy", "models/smiley", pos=(5, 5, 2), scale=1.5)
        enemy.node.setColorScale(0.8, 0.2, 0.2, 1)  # Red

        box = GameObject("Crate", "models/box", pos=(-5, 5, 0), scale=2)
        box.node.setColorScale(0.4, 0.2, 0.1, 1)  # Brown

        # Start
        for obj in self.all_objects: obj._start()

    def setup_editor(self):
        self.editor = EngineEditor()
        # Default selection for Inspector
        self.editor.selected_obj = self.player

    def game_loop(self, task):
        dt = self.globalClock.getDt()
        for obj in self.all_objects:
            obj._update(dt)
        return Task.cont


# Run it
if __name__ == "__main__":
    app = Engine()
    app.run()