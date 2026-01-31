# aurora_engine/ui/image.py

from aurora_engine.ui.widget import Widget
from aurora_engine.core.logging import get_logger
from panda3d.core import NodePath, Texture, CardMaker, TransparencyAttrib, Vec4
import builtins
import os

logger = get_logger()

class ImageWidget(Widget):
    """
    Widget that renders a 2D image (PNG/JPG).
    Uses Panda3D's pixel2d for pixel-perfect positioning.
    """
    
    # Static set to track missing images and prevent spam
    _missing_images_logged = set()
    
    def __init__(self, name: str, image_path: str):
        super().__init__(name)
        self.image_path = image_path
        self._node_path: NodePath = None
        self._texture: Texture = None
        self._loaded = False
        self.color = (1.0, 1.0, 1.0, 1.0) # Tint color
        self.rotation = 0.0 # Degrees
        self.z_index = 0 # Draw order

    def _load_resources(self):
        if self._loaded: return
        
        if hasattr(builtins, 'base'):
            try:
                # Check if file exists first to avoid Panda3D screaming
                if not os.path.exists(self.image_path):
                    if self.image_path not in ImageWidget._missing_images_logged:
                        logger.warning(f"Image/Texture missing: {self.image_path}")
                        ImageWidget._missing_images_logged.add(self.image_path)
                    return 

                # Load texture
                self._texture = builtins.base.loader.loadTexture(self.image_path)
                
                # Create a quad
                cm = CardMaker(self.name)
                # Set frame so (0,0) is top-left and (1,1) is bottom-right in UV space
                # In geometry: 0 to 1 in X, 0 to -1 in Z (since pixel2d Y is Z-axis down)
                cm.setFrame(0, 1, -1, 0) 
                
                self._node_path = NodePath(cm.generate())
                self._node_path.setTexture(self._texture)
                self._node_path.setTransparency(TransparencyAttrib.MAlpha)
                
                # Parent to pixel2d for pixel coordinates
                self._node_path.reparentTo(builtins.base.pixel2d)
                
                self._loaded = True
            except Exception as e:
                # Fallback for other errors
                if self.image_path not in ImageWidget._missing_images_logged:
                    logger.warning(f"Failed to load image {self.image_path}: {e}")
                    ImageWidget._missing_images_logged.add(self.image_path)

    def _render_self(self):
        self._load_resources()
        
        if self._node_path:
            if not self.visible:
                self._node_path.hide()
                return
            
            self._node_path.show()
            
            pos = self.get_screen_position()
            
            # pixel2d coordinates: 
            # X+ is Right
            # Z- is Down (Screen Y)
            # Y is Depth (Sort Order)
            
            # Position
            self._node_path.setPos(pos[0], 0, -pos[1])
            
            # Scale (Size)
            self._node_path.setScale(self.size[0], 1, self.size[1])
            
            # Rotation (around pivot)
            # TODO: Implement pivot support in geometry or offset
            self._node_path.setR(self.rotation)
            
            # Color/Alpha
            self._node_path.setColor(Vec4(*self.color))
            
            # Z-Index (Binning)
            self._node_path.setBin("fixed", self.z_index)

    def set_image(self, image_path: str):
        """Change the image dynamically."""
        if self.image_path == image_path:
            return
            
        self.image_path = image_path
        if self._node_path and hasattr(builtins, 'base'):
            try:
                if not os.path.exists(self.image_path):
                    if self.image_path not in ImageWidget._missing_images_logged:
                        logger.warning(f"Image/Texture missing: {self.image_path}")
                        ImageWidget._missing_images_logged.add(self.image_path)
                    return

                self._texture = builtins.base.loader.loadTexture(self.image_path)
                self._node_path.setTexture(self._texture, 1) # 1 = override
            except Exception as e:
                if self.image_path not in ImageWidget._missing_images_logged:
                    logger.warning(f"Failed to load image {self.image_path}: {e}")
                    ImageWidget._missing_images_logged.add(self.image_path)

    def destroy(self):
        """Cleanup resources."""
        if self._node_path:
            self._node_path.removeNode()
            self._node_path = None
        self._loaded = False
