# aurora_engine/core/logging.py

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


class Logger:
    """
    Engine logging system.
    Provides categorized logging with file output.
    """

    def __init__(self, name: str = "AuroraEngine", log_dir: str = "logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self):
        """Setup console and file handlers."""
        # Console handler (INFO and above)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(levelname)-8s [%(name)s] %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler (DEBUG and above)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"engine_{timestamp}.log"

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)-8s [%(name)s:%(funcName)s:%(lineno)d] %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

    def debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)

    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)

    def warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)

    def error(self, message: str, exc_info: bool = False):
        """Log error message."""
        self.logger.error(message, exc_info=exc_info)

    def critical(self, message: str, exc_info: bool = False):
        """Log critical message."""
        self.logger.critical(message, exc_info=exc_info)


# Global logger instance
_logger: Optional[Logger] = None


def get_logger() -> Logger:
    """Get global engine logger."""
    global _logger
    if _logger is None:
        _logger = Logger()
    return _logger


def init_logger(name: str = "AuroraEngine", log_dir: str = "logs") -> Logger:
    """Initialize global logger."""
    global _logger
    _logger = Logger(name, log_dir)
    return _logger