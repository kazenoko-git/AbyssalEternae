from engine.ecs.System import System
from engine.input.InputState import InputState
from engine.input.KeyMap import KeyMap


class InputSystem(System):
    def __init__(self, base):
        self.Base = base
        self.State = InputState()

        self._PrevMouse = None

    def Update(self, world):
        mw = self.Base.mouseWatcherNode
        if not mw:
            return

        # --- Keyboard ---
        self.State.Actions[KeyMap.Forward] = mw.isButtonDown(KeyMap.Forward)
        self.State.Actions[KeyMap.Backward] = mw.isButtonDown(KeyMap.Backward)
        self.State.Actions[KeyMap.Left] = mw.isButtonDown(KeyMap.Left)
        self.State.Actions[KeyMap.Right] = mw.isButtonDown(KeyMap.Right)
        self.State.Actions[KeyMap.Jump] = mw.isButtonDown(KeyMap.Jump)

        # --- Mouse buttons ---
        self.State.Actions[KeyMap.MouseLeft] = mw.isButtonDown(KeyMap.MouseLeft)
        self.State.Actions[KeyMap.MouseRight] = mw.isButtonDown(KeyMap.MouseRight)

        # --- Mouse movement ---
        if mw.hasMouse():
            x = mw.getMouseX()
            y = mw.getMouseY()

            if self._PrevMouse is None:
                self._PrevMouse = (x, y)

            dx = x - self._PrevMouse[0]
            dy = y - self._PrevMouse[1]

            self.State.MouseDelta = (dx, dy)
            self._PrevMouse = (x, y)
        else:
            self.State.MouseDelta = (0, 0)

    def FixedUpdate(self, world):
        pass
