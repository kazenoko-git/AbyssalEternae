import numpy as np
from aurora_engine.ui.image import ImageWidget
from aurora_engine.ui.ui_manager import UIManager
from aurora_engine.core.config import Config

class GameUIManager:
    """
    Manages the game-specific UI elements like HUD, minimap, etc.
    """
    def __init__(self, ui_manager: UIManager, config: Config):
        self.ui = ui_manager
        self.config = config

    def setup_ui(self):
        """Initialize basic game UI."""
        # Crosshair
        crosshair = ImageWidget("Crosshair", "assets/ui/crosshair.png")
        crosshair.size = np.array([32, 32], dtype=np.float32)
        w = self.config.get('rendering.width', 1280)
        h = self.config.get('rendering.height', 720)
        crosshair.position = np.array([w/2 - 16, h/2 - 16], dtype=np.float32)
        self.ui.add_widget(crosshair, layer='overlay')
        
        # Health Bar (Background)
        hp_bg = ImageWidget("HP_BG", "assets/ui/bar_bg.png")
        hp_bg.size = np.array([300, 30], dtype=np.float32)
        hp_bg.position = np.array([50, h - 50], dtype=np.float32)
        hp_bg.color = (0.2, 0.2, 0.2, 0.8)
        self.ui.add_widget(hp_bg, layer='hud')
        
        # Health Bar (Fill)
        hp_fill = ImageWidget("HP_Fill", "assets/ui/bar_fill.png")
        hp_fill.size = np.array([300, 30], dtype=np.float32)
        hp_fill.position = np.array([50, h - 50], dtype=np.float32)
        hp_fill.color = (0.8, 0.2, 0.2, 1.0)
        self.ui.add_widget(hp_fill, layer='hud')
        
        # Minimap Frame
        minimap = ImageWidget("Minimap", "assets/ui/minimap_frame.png")
        minimap.size = np.array([200, 200], dtype=np.float32)
        minimap.position = np.array([w - 220, 20], dtype=np.float32)
        self.ui.add_widget(minimap, layer='hud')
