# aurora_engine/rendering/shader.py

from typing import Dict, Any
from panda3d.core import Shader as PandaShader
from aurora_engine.core.logging import get_logger

logger = get_logger()

class Shader:
    """
    Shader program abstraction.
    Wraps Panda3D shader objects with a cleaner API.
    """

    def __init__(self, name: str, vertex_path: str, fragment_path: str):
        self.name = name
        self.vertex_path = vertex_path
        self.fragment_path = fragment_path

        # Shader parameters
        self.uniforms: Dict[str, Any] = {}

        # Backend handle (Panda3D shader object)
        self._backend_shader = None
        # logger.debug(f"Shader '{name}' created")

    def compile(self):
        """Compile shader from source files."""
        try:
            self._backend_shader = PandaShader.load(
                PandaShader.SL_GLSL,
                vertex=self.vertex_path,
                fragment=self.fragment_path
            )
            logger.info(f"Compiled shader '{self.name}'")
        except Exception as e:
            logger.error(f"Failed to compile shader {self.name}: {e}")

    def set_uniform(self, name: str, value: Any):
        """Set shader uniform value."""
        self.uniforms[name] = value

    def bind(self, node_path):
        """Activate this shader for rendering on a specific NodePath."""
        if self._backend_shader and node_path:
            node_path.setShader(self._backend_shader)
            
            # Apply uniforms
            for name, value in self.uniforms.items():
                node_path.setShaderInput(name, value)
