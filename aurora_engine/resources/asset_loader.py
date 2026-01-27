# aurora_engine/resources/asset_loader.py

from typing import Any
import os
import json
from aurora_engine.rendering.mesh import Mesh, create_cube_mesh, create_sphere_mesh, create_plane_mesh
from aurora_engine.rendering.shader import Shader
from aurora_engine.rendering.material import Material


class AssetLoader:
    """
    Handles loading of specific asset types.
    """

    @staticmethod
    def load_mesh(path: str) -> Mesh:
        """Load a mesh from file."""
        # Simple procedural fallback for testing
        if path == "cube":
            return create_cube_mesh()
        elif path == "sphere":
            return create_sphere_mesh()
        elif path == "plane":
            return create_plane_mesh()
            
        # TODO: Implement OBJ/GLTF loading
        # For now, return a cube as placeholder
        print(f"Warning: Mesh loading not implemented for {path}, returning cube.")
        return create_cube_mesh()

    @staticmethod
    def load_shader(path: str) -> Shader:
        """Load a shader from file."""
        # Assuming path points to a directory or base name
        # e.g. "shaders/basic" -> "shaders/basic.vert", "shaders/basic.frag"
        
        vert_path = f"{path}.vert"
        frag_path = f"{path}.frag"
        
        name = os.path.basename(path)
        shader = Shader(name, vert_path, frag_path)
        shader.compile()
        return shader

    @staticmethod
    def load_material(path: str) -> Material:
        """Load a material from JSON definition."""
        if not os.path.exists(path):
            # Return default material
            shader = AssetLoader.load_shader("shaders/default")
            return Material("Default", shader)
            
        with open(path, 'r') as f:
            data = json.load(f)
            
        shader_path = data.get('shader', 'shaders/default')
        shader = AssetLoader.load_shader(shader_path)
        
        material = Material(data.get('name', 'Material'), shader)
        
        # Load properties
        props = data.get('properties', {})
        for name, value in props.items():
            material.set_property(name, value)
            
        return material
