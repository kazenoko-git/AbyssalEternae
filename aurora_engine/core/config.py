# aurora_engine/core/config.py

import json
import os
from pathlib import Path
from typing import Any, Dict
from aurora_engine.core.logging import get_logger

logger = get_logger()

class Config:
    """
    Engine configuration management.
    Handles loading/saving settings from files.
    """

    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.data: Dict[str, Any] = {}

        # Default configuration
        self.defaults = {
            'engine': {
                'version': '0.1.0',
                'log_level': 'INFO',
                'fixed_timestep': 1 / 60.0,
            },
            'rendering': {
                'width': 1920,
                'height': 1080,
                'fullscreen': False,
                'vsync': True,
                'msaa_samples': 4,
                'max_fps': 144,
                'title': 'Aurora Engine',
            },
            'physics': {
                'gravity': [0.0, 0.0, -9.81],
                'simulation_substeps': 1,
            },
            'audio': {
                'master_volume': 1.0,
                'music_volume': 0.7,
                'sfx_volume': 1.0,
            },
            'input': {
                'mouse_sensitivity': 1.0,
                'controller_deadzone': 0.15,
            },
            'world': {
                'chunk_size': 100.0,
                'load_radius': 3,
                'unload_radius': 5,
            },
            'database': {
                'path': 'game.db',
            }
        }

        self.load()

    def load(self):
        """Load configuration from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    loaded_data = json.load(f)

                # Merge with defaults (loaded values override defaults)
                self.data = self._deep_merge(self.defaults.copy(), loaded_data)
                logger.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                logger.error(f"Failed to load configuration from {self.config_path}: {e}")
                self.data = self.defaults.copy()
        else:
            # Use defaults
            self.data = self.defaults.copy()
            logger.info(f"Configuration file not found, using defaults and creating {self.config_path}")
            self.save()  # Create default config file

    def save(self):
        """Save configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.data, f, indent=2)
            logger.info(f"Saved configuration to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration to {self.config_path}: {e}")

    def get(self, path: str, default: Any = None) -> Any:
        """
        Get configuration value by path.
        Example: config.get('rendering.width')
        """
        keys = path.split('.')
        value = self.data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, path: str, value: Any):
        """
        Set configuration value by path.
        Example: config.set('rendering.width', 2560)
        """
        keys = path.split('.')
        data = self.data

        for key in keys[:-1]:
            if key not in data:
                data[key] = {}
            data = data[key]

        data[keys[-1]] = value

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Recursively merge override dict into base dict."""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result
