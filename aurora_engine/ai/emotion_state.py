# aurora_engine/ai/emotion_state.py

from enum import Enum
from typing import Dict
import numpy as np


class Emotion(Enum):
    """Basic emotion types."""
    NEUTRAL = 0
    HAPPY = 1
    SAD = 2
    ANGRY = 3
    FEARFUL = 4
    SURPRISED = 5
    DISGUSTED = 6


class EmotionState:
    """
    NPC emotional state system.
    Tracks emotions with intensity and decay.
    """

    def __init__(self):
        # Current emotion intensities (0-1)
        self.emotions: Dict[Emotion, float] = {
            emotion: 0.0 for emotion in Emotion
        }
        self.emotions[Emotion.NEUTRAL] = 1.0

        # Decay rates
        self.decay_rate = 0.1  # Per second

        # Personality modifiers (affects how emotions are processed)
        self.personality = {
            'excitability': 0.5,  # How easily emotions intensify
            'stability': 0.5,  # How quickly emotions decay
            'positivity': 0.5,  # Bias toward positive emotions
        }

    def add_emotion(self, emotion: Emotion, intensity: float):
        """Add emotional intensity."""
        intensity *= self.personality['excitability']

        # Apply positivity bias
        if emotion in [Emotion.HAPPY, Emotion.SURPRISED]:
            intensity *= (1.0 + self.personality['positivity'] * 0.5)
        elif emotion in [Emotion.SAD, Emotion.ANGRY, Emotion.FEARFUL]:
            intensity *= (1.0 - self.personality['positivity'] * 0.3)

        self.emotions[emotion] = min(1.0, self.emotions[emotion] + intensity)

        # Reduce neutral
        self.emotions[Emotion.NEUTRAL] = max(0.0, self.emotions[Emotion.NEUTRAL] - intensity * 0.5)

    def update(self, dt: float):
        """Update emotion decay."""
        decay = self.decay_rate * self.personality['stability'] * dt

        for emotion in Emotion:
            if emotion == Emotion.NEUTRAL:
                continue

            # Decay emotion
            self.emotions[emotion] = max(0.0, self.emotions[emotion] - decay)

        # Normalize to ensure they sum to reasonable range
        total = sum(self.emotions.values())
        if total > 0:
            for emotion in Emotion:
                self.emotions[emotion] /= total

        # Restore neutral if all emotions are low
        if sum(self.emotions.values()) < 0.5:
            self.emotions[Emotion.NEUTRAL] = 1.0 - sum(
                v for k, v in self.emotions.items() if k != Emotion.NEUTRAL
            )

    def get_dominant_emotion(self) -> Emotion:
        """Get current dominant emotion."""
        return max(self.emotions.items(), key=lambda x: x[1])[0]

    def get_emotion_vector(self) -> np.ndarray:
        """Get emotion state as vector (for AI input)."""
        return np.array([self.emotions[e] for e in Emotion], dtype=np.float32)

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            'emotions': {e.name: v for e, v in self.emotions.items()},
            'personality': self.personality.copy()
        }

    @staticmethod
    def from_dict(data: Dict) -> 'EmotionState':
        """Deserialize from dictionary."""
        state = EmotionState()

        if 'emotions' in data:
            for name, value in data['emotions'].items():
                emotion = Emotion[name]
                state.emotions[emotion] = value

        if 'personality' in data:
            state.personality.update(data['personality'])

        return state