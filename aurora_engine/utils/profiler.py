# aurora_engine/utils/profiler.py

import time
from typing import Dict
from collections import defaultdict
from aurora_engine.core.logging import get_logger

logger = get_logger()

class Profiler:
    """
    Simple performance profiler for engine systems.
    """

    def __init__(self):
        self.timings: Dict[str, list] = defaultdict(list)
        self.current_frames: Dict[str, float] = {}
        self.enabled = True

    def begin(self, section_name: str):
        """Start timing a section."""
        if not self.enabled:
            return
        self.current_frames[section_name] = time.perf_counter()

    def end(self, section_name: str):
        """End timing a section."""
        if not self.enabled or section_name not in self.current_frames:
            return

        elapsed = time.perf_counter() - self.current_frames[section_name]
        self.timings[section_name].append(elapsed * 1000.0)  # Convert to ms

        # Keep only last 60 frames
        if len(self.timings[section_name]) > 60:
            self.timings[section_name].pop(0)

        del self.current_frames[section_name]

    def get_average(self, section_name: str) -> float:
        """Get average time for a section."""
        if section_name not in self.timings or not self.timings[section_name]:
            return 0.0
        return sum(self.timings[section_name]) / len(self.timings[section_name])

    def print_report(self):
        """Print performance report."""
        report = "\n=== Performance Report ===\n"
        for section, times in sorted(self.timings.items()):
            avg_time = self.get_average(section)
            max_time = max(times) if times else 0.0
            min_time = min(times) if times else 0.0

            report += f"{section:30s}: avg={avg_time:6.2f}ms  min={min_time:6.2f}ms  max={max_time:6.2f}ms\n"
        report += "==========================\n"
        logger.info(report)


# Global profiler instance
_profiler = Profiler()


def profile_section(name: str):
    """Context manager for profiling."""

    class ProfileContext:
        def __enter__(self):
            _profiler.begin(name)
            return self

        def __exit__(self, *args):
            _profiler.end(name)

    return ProfileContext()


# Usage in application
def update_with_profiling(self, dt: float, alpha: float):
    """Update with profiling."""
    with profile_section("Input"):
        self.input.update(dt)

    with profile_section("UI"):
        self.ui.update(dt)

    with profile_section("Systems"):
        self.world.update_systems(dt)

    # Print report every 60 frames
    if self.frame_count % 60 == 0:
        _profiler.print_report()
