# aurora_engine/physics/raycast.py

import numpy as np
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class RaycastHit:
    """Information about a raycast hit."""

    point: np.ndarray  # Hit point in world space
    normal: np.ndarray  # Surface normal at hit point
    distance: float  # Distance from ray origin
    entity: 'Entity'  # Entity that was hit
    collider: 'Collider'  # Collider component that was hit


class Raycast:
    """
    Raycast utilities for physics queries.
    """

    @staticmethod
    def cast(physics_world: 'PhysicsWorld',
             origin: np.ndarray,
             direction: np.ndarray,
             max_distance: float = 1000.0,
             layer_mask: int = 0xFFFFFFFF) -> Optional[RaycastHit]:
        """
        Cast a ray and return first hit.

        Args:
            physics_world: Physics world to query
            origin: Ray start position
            direction: Ray direction (should be normalized)
            max_distance: Maximum ray distance
            layer_mask: Layer mask for filtering

        Returns:
            RaycastHit if hit, None otherwise
        """
        if physics_world._bullet_world is None:
            return None

        from panda3d.bullet import BulletWorld
        from panda3d.core import Point3, Vec3

        # Normalize direction
        direction = direction / np.linalg.norm(direction)
        end = origin + direction * max_distance

        # Convert to Panda3D types
        panda_origin = Point3(origin[0], origin[1], origin[2])
        panda_end = Point3(end[0], end[1], end[2])

        # Perform raycast
        result = physics_world._bullet_world.rayTestClosest(panda_origin, panda_end)

        if result.hasHit():
            hit_point = result.getHitPos()
            hit_normal = result.getHitNormal()

            # Find entity from collider
            node = result.getNode()
            entity = physics_world._node_to_entity.get(node)

            if entity:
                collider = entity.get_component(Collider)

                return RaycastHit(
                    point=np.array([hit_point.x, hit_point.y, hit_point.z]),
                    normal=np.array([hit_normal.x, hit_normal.y, hit_normal.z]),
                    distance=np.linalg.norm(origin - np.array([hit_point.x, hit_point.y, hit_point.z])),
                    entity=entity,
                    collider=collider
                )

        return None

    @staticmethod
    def cast_all(physics_world: 'PhysicsWorld',
                 origin: np.ndarray,
                 direction: np.ndarray,
                 max_distance: float = 1000.0,
                 layer_mask: int = 0xFFFFFFFF) -> List[RaycastHit]:
        """
        Cast a ray and return all hits.
        """
        if physics_world._bullet_world is None:
            return []

        from panda3d.bullet import BulletWorld
        from panda3d.core import Point3, Vec3

        direction = direction / np.linalg.norm(direction)
        end = origin + direction * max_distance

        panda_origin = Point3(origin[0], origin[1], origin[2])
        panda_end = Point3(end[0], end[1], end[2])

        result = physics_world._bullet_world.rayTestAll(panda_origin, panda_end)

        hits = []
        if result.hasHits():
            for i in range(result.getNumHits()):
                hit = result.getHit(i)
                hit_point = hit.getHitPos()
                hit_normal = hit.getHitNormal()

                node = hit.getNode()
                entity = physics_world._node_to_entity.get(node)

                if entity:
                    collider = entity.get_component(Collider)

                    hits.append(RaycastHit(
                        point=np.array([hit_point.x, hit_point.y, hit_point.z]),
                        normal=np.array([hit_normal.x, hit_normal.y, hit_normal.z]),
                        distance=np.linalg.norm(origin - np.array([hit_point.x, hit_point.y, hit_point.z])),
                        entity=entity,
                        collider=collider
                    ))

        # Sort by distance
        hits.sort(key=lambda h: h.distance)
        return hits

    @staticmethod
    def sphere_cast(physics_world: 'PhysicsWorld',
                    origin: np.ndarray,
                    radius: float,
                    direction: np.ndarray,
                    max_distance: float = 1000.0) -> Optional[RaycastHit]:
        """
        Cast a sphere along a ray.
        Useful for thick raycasts (e.g., character movement).
        """
        # TODO: Implement sphere cast using Bullet sweep test
        pass