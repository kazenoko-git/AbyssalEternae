class SceneManager:
    def __init__(self):
        self._CurrentScene = None

    def LoadScene(self, scene):
        if self._CurrentScene:
            self._CurrentScene.Unload()

        self._CurrentScene = scene
        self._CurrentScene.Load()

    def Update(self):
        if self._CurrentScene:
            self._CurrentScene.Update()

    def FixedUpdate(self):
        if self._CurrentScene:
            self._CurrentScene.FixedUpdate()
