from panda3d.core import loadPrcFileData

loadPrcFileData("", "gl-version 2 1")
loadPrcFileData("", "glsl-version 120")

from ursina import *
from game.core.GameManager import GameManager
from game.core.GameState import GameState

from ursina import held_keys, time

def PlayerMove():
    speed = 8 * time.dt
    if held_keys['w']:
        Player.z += speed
    if held_keys['s']:
        Player.z -= speed
    if held_keys['a']:
        Player.x -= speed
    if held_keys['d']:
        Player.x += speed


app = Ursina()
window.vsync = True
window.borderless = False
window.fullscreen = False
DirectionalLight(direction=(0.4, -1, 0.4))


Player = Entity(
    model='cube',
    color=color.orange,
    scale=1,
    position=(0, 2, 0)
)

camera.parent = Player
camera.position = (0, 15, -20)
camera.rotation_x = 30

GameState.Player = Player

Game = GameManager()
Game.Init()


def update():
    PlayerMove()
    Game.Update()


app.run()
