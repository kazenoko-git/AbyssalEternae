from ursina import *

from game.core.GameManager import GameManager

app = Ursina()

Game = GameManager()
Game.Init()


def update():
    Game.Update()


app.run()
