from engine.ecs.System import System
from engine.ecs.components.Transform import Transform
from engine.ecs.components.Movement import Movement
from engine.ecs.components.Player import Player
from engine.input.KeyMap import KeyMap
from engine.core.Time import Time


class MovementSystem(System):
    def __init__(self, inputState):
        self.Input = inputState

    def Update(self, world):
        for entityId in world.Query(Transform, Movement, Player):
            transform = world._Components[Transform][entityId]
            movement = world._Components[Movement][entityId]

            dx = 0.0
            dy = 0.0

            if self.Input.IsDown(KeyMap.Forward):
                dy += 1
            if self.Input.IsDown(KeyMap.Backward):
                dy -= 1
            if self.Input.IsDown(KeyMap.Left):
                dx -= 1
            if self.Input.IsDown(KeyMap.Right):
                dx += 1

            # Normalize (prevents faster diagonal movement)
            length = (dx * dx + dy * dy) ** 0.5
            if length > 0:
                dx /= length
                dy /= length

            speed = movement.Speed * Time.Delta

            transform.Position[0] += dx * speed
            transform.Position[1] += dy * speed

    def FixedUpdate(self, world):
        pass
