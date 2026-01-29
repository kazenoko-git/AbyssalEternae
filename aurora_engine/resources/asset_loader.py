# aurora_engine/resources/asset_loader.py

from typing import Any, Optional
import os
import json
from aurora_engine.rendering.mesh import Mesh, create_cube_mesh, create_sphere_mesh, create_plane_mesh
from aurora_engine.rendering.shader import Shader
from aurora_engine.rendering.material import Material
from panda3d.core import NodePath
from aurora_engine.core.logging import get_logger

logger = get_logger()

class AssetLoader:
    """
    Handles loading of specific asset types.
    """

    @staticmethod
    def load_model(path: str) -> Optional[NodePath]:
        """
        Load a 3D model using Panda3D's loader.
        Supports .egg, .bam, .gltf, .obj (if plugins installed).
        """
        # Access global loader from ShowBase
        try:
            import builtins
            if hasattr(builtins, 'base'):
                # Panda3D loader caches automatically
                model = builtins.base.loader.loadModel(path)
                logger.info(f"Loaded model: {path}")
                return model
        except Exception as e:
            logger.error(f"Failed to load model {path}: {e}")
        return None

    @staticmethod
    def load_mesh(path: str) -> Mesh:
        """Load a mesh from file (Legacy/Procedural fallback)."""
        # Simple procedural fallback for testing
        if path == "cube":
            return create_cube_mesh()
        elif path == "sphere":
            return create_sphere_mesh()
        elif path == "plane":
            return create_plane_mesh()
            
        # For actual files, we prefer load_model which returns a NodePath.
        # If we need a Mesh object (raw data), we'd need to extract it from the NodePath.
        # For now, we assume this is used for procedural fallbacks.
        logger.warning(f"Mesh loading not implemented for {path}, returning cube.")
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
            logger.warning(f"Material file not found: {path}, using default")
            shader = AssetLoader.load_shader("shaders/default")
            return Material("Default", shader)
            
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                
            shader_path = data.get('shader', 'shaders/default')
            shader = AssetLoader.load_shader(shader_path)
            
            material = Material(data.get('name', 'Material'), shader)
            
            # Load properties
            props = data.get('properties', {})
            for name, value in props.items():
                material.set_property(name, value)
                
            logger.info(f"Loaded material: {path}")
            return material
        except Exception as e:
            logger.error(f"Failed to load material {path}: {e}")
            shader = AssetLoader.load_shader("shaders/default")
            return Material("Error", shader)
