class InputState:
    def __init__(self):
        self.Actions = {}
        self.MouseDelta = (0, 0)

    def IsDown(self, action):
        return self.Actions.get(action, False)
