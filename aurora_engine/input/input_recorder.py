# aurora_engine/input/input_recorder.py

from typing import List, BinaryIO
import struct
import time
from aurora_engine.core.logging import get_logger

logger = get_logger()

class InputFrame:
    """Single frame of input data."""

    def __init__(self, frame_number: int, timestamp: float, input_state: dict):
        self.frame_number = frame_number
        self.timestamp = timestamp
        self.input_state = input_state.copy()


class InputRecorder:
    """
    Records and plays back input sequences.
    Useful for:
    - Replay systems
    - Demo modes
    - AI training
    - Bug reproduction
    """

    def __init__(self):
        self.recording = False
        self.playing_back = False

        self.recorded_frames: List[InputFrame] = []
        self.playback_index = 0

        self.start_time = 0.0
        self.frame_count = 0

    def start_recording(self):
        """Start recording input."""
        self.recording = True
        self.recorded_frames.clear()
        self.start_time = time.perf_counter()
        self.frame_count = 0
        logger.info("Started input recording")

    def stop_recording(self):
        """Stop recording input."""
        self.recording = False
        logger.info(f"Stopped input recording. Recorded {len(self.recorded_frames)} frames.")

    def record_frame(self, input_state: dict):
        """Record current frame's input state."""
        if not self.recording:
            return

        frame = InputFrame(
            frame_number=self.frame_count,
            timestamp=time.perf_counter() - self.start_time,
            input_state=input_state
        )

        self.recorded_frames.append(frame)
        self.frame_count += 1

    def start_playback(self):
        """Start playing back recorded input."""
        if not self.recorded_frames:
            logger.warning("Cannot start playback: No frames recorded")
            return

        self.playing_back = True
        self.playback_index = 0
        self.start_time = time.perf_counter()
        logger.info("Started input playback")

    def stop_playback(self):
        """Stop playback."""
        self.playing_back = False
        self.playback_index = 0
        logger.info("Stopped input playback")

    def get_playback_input(self) -> dict:
        """Get input state for current playback frame."""
        if not self.playing_back or self.playback_index >= len(self.recorded_frames):
            self.stop_playback()
            return {}

        current_time = time.perf_counter() - self.start_time
        frame = self.recorded_frames[self.playback_index]

        # Check if we should advance to next frame
        if current_time >= frame.timestamp:
            self.playback_index += 1

        return frame.input_state

    def save_to_file(self, filepath: str):
        """Save recorded input to file."""
        try:
            with open(filepath, 'wb') as f:
                # Write header
                f.write(struct.pack('I', len(self.recorded_frames)))

                # Write frames
                for frame in self.recorded_frames:
                    f.write(struct.pack('I', frame.frame_number))
                    f.write(struct.pack('d', frame.timestamp))

                    # Serialize input state (simplified - needs proper serialization)
                    import json
                    state_json = json.dumps(frame.input_state)
                    state_bytes = state_json.encode('utf-8')
                    f.write(struct.pack('I', len(state_bytes)))
                    f.write(state_bytes)
            logger.info(f"Saved input recording to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save input recording to {filepath}: {e}")

    def load_from_file(self, filepath: str):
        """Load recorded input from file."""
        import json
        try:
            with open(filepath, 'rb') as f:
                # Read header
                num_frames = struct.unpack('I', f.read(4))[0]

                self.recorded_frames.clear()

                # Read frames
                for _ in range(num_frames):
                    frame_number = struct.unpack('I', f.read(4))[0]
                    timestamp = struct.unpack('d', f.read(8))[0]

                    state_len = struct.unpack('I', f.read(4))[0]
                    state_bytes = f.read(state_len)
                    state_json = state_bytes.decode('utf-8')
                    input_state = json.loads(state_json)

                    frame = InputFrame(frame_number, timestamp, input_state)
                    self.recorded_frames.append(frame)
            logger.info(f"Loaded input recording from {filepath} ({len(self.recorded_frames)} frames)")
        except Exception as e:
            logger.error(f"Failed to load input recording from {filepath}: {e}")
