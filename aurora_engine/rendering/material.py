# aurora_engine/rendering/material.py

from typing import Dict, Any, Optional
from aurora_engine.rendering.shader import Shader
from panda3d.core import RenderState, ColorBlendAttrib, CullFaceAttrib
from aurora_engine.core.logging import get_logger

logger = get_logger()

class MaterialProperty:
    """A single material property (color, texture, float, etc.)."""

    def __init__(self, name: str, value: Any):
        self.name = name
        self.value = value


class Material:
    """
    Material definition (Unity-style).
    Contains shader reference and property values.
    """

    def __init__(self, name: str, shader: Shader):
        self.name = name
        self.shader = shader

        # Material properties (exposed to inspector/editor)
        self.properties: Dict[str, MaterialProperty] = {}

        # Render state
        self.render_queue = 2000  # Opaque = 2000, Transparent = 3000
        self.cull_mode = "back"  # "back", "front", "none"
        self.depth_write = True
        self.blend_mode = "opaque"  # "opaque", "alpha", "additive"
        
        # logger.debug(f"Material '{name}' created with shader '{shader.name}'")

    def set_property(self, name: str, value: Any):
        """Set material property."""
        if name not in self.properties:
            self.properties[name] = MaterialProperty(name, value)
        else:
            self.properties[name].value = value

    def get_property(self, name: str) -> Optional[Any]:
        """Get material property value."""
        prop = self.properties.get(name)
        return prop.value if prop else None

    def apply(self, node_path):
        """Apply material to a Panda3D NodePath."""
        if not node_path:
            return

        # Apply shader
        self.shader.bind(node_path)

        # Set shader uniforms from material properties
        for prop in self.properties.values():
            # TODO: Handle different types (textures, colors, etc.)
            node_path.setShaderInput(prop.name, prop.value)
            
        # Apply render state
        state = self._create_render_state()
        node_path.setState(state)

    def _create_render_state(self) -> RenderState:
        """Create Panda3D RenderState from material properties."""
        state = RenderState.makeEmpty()
        
        # Cull mode
        if self.cull_mode == "back":
            state = state.addAttrib(CullFaceAttrib.make(CullFaceAttrib.MCullCounterClockwise))
        elif self.cull_mode == "front":
            state = state.addAttrib(CullFaceAttrib.make(CullFaceAttrib.MCullClockwise))
        elif self.cull_mode == "none":
            state = state.addAttrib(CullFaceAttrib.make(CullFaceAttrib.MCullNone))
            
        # Blend mode
        if self.blend_mode == "alpha":
            state = state.addAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OIncomingAlpha, ColorBlendAttrib.OOneMinusIncomingAlpha))
        elif self.blend_mode == "additive":
            state = state.addAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OOne, ColorBlendAttrib.OOne))
            
        # Depth write
        # TODO: Set depth write state
        
        return state
