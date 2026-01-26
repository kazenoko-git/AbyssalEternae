from core import Component
from panda3d.core import CollisionNode, CollisionSphere, CollisionHandlerPusher, BitMask32, Vec3
import math


# ==================================================================================
# 🎮 RPG COMPONENTS
# ==================================================================================

class PlayerController(Component):
    def start(self):
        self.speed = 10
        self.turn_speed = 200

        # Physics Collider
        self.col_node = self.transform.attachNewNode(CollisionNode('player_cnode'))
        self.col_node.node().addSolid(CollisionSphere(0, 0, 1, 1))
        self.col_node.setCollideMask(BitMask32.bit(0))

        # Gravity Handler
        self.handler = CollisionHandlerPusher()
        self.handler.addCollider(self.col_node, self.transform)
        base.cTrav.addCollider(self.col_node, self.handler)

    def update(self, dt):
        if base.engine.editor_active: return  # Freeze controls when editing

        # Rotation
        rotate = 0
        if base.input.get_key("arrow_left") or base.input.get_key("a"): rotate += 1
        if base.input.get_key("arrow_right") or base.input.get_key("d"): rotate -= 1
        self.transform.setH(self.transform.getH() + rotate * self.turn_speed * dt)

        # Movement
        move = 0
        if base.input.get_key("arrow_up") or base.input.get_key("w"): move += 1
        if base.input.get_key("arrow_down") or base.input.get_key("s"): move -= 1

        if move != 0:
            self.transform.setY(self.transform, move * self.speed * dt)


class ThirdPersonCamera(Component):
    def start(self):
        self.target = self.transform
        self.distance = 20
        self.height = 8
        self.lag = 5.0

        # Unparent camera from player so it doesn't jitter
        base.camera.reparentTo(base.render)

    def update(self, dt):
        # Desired Position
        target_pos = self.target.getPos()
        # Offset behind player based on player's facing
        angle_rad = math.radians(self.target.getH())

        # Simple math to place camera behind
        cam_x = target_pos.x + math.sin(angle_rad) * self.distance
        cam_y = target_pos.y - math.cos(angle_rad) * self.distance
        cam_z = target_pos.z + self.height

        # Smooth interpolation
        current_pos = base.camera.getPos()
        target_vec = Vec3(cam_x, cam_y, cam_z)
        new_pos = current_pos + (target_vec - current_pos) * dt * self.lag

        base.camera.setPos(new_pos)
        base.camera.lookAt(target_pos + Vec3(0, 0, 2))