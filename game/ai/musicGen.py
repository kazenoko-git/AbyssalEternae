from pathlib import Path
import hashlib
import json
import random
from dataclasses import dataclass
from typing import List, Dict, Optional

from pydub import AudioSegment

# =========================
# PATHS
# =========================

BASE = Path(__file__).resolve().parents[2]  # game/
MUSIC_DIR = BASE / "audio" / "music"
STEM_DIR = MUSIC_DIR / "stems"
TRACK_DIR = MUSIC_DIR / "generated" / "tracks"

TRACK_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# DATA MODELS
# =========================

@dataclass(frozen=True)
class MusicContext:
    biome: str
    danger: float
    narrative: str
    dimension: str
    seed: int


# =========================
# TRACK PROFILES
# =========================

TRACK_PROFILES: Dict[str, Dict] = {
    "exploration": {
        "required": ["strings_pad_mid", "choir_airy"],
        "optional": ["piano_sparse", "harp_pluck", "strings_pad_high"],
        "max_layers": 4
    },
    "tension": {
        "required": ["strings_pad_low", "strings_pulse"],
        "optional": ["brass_sustain_low", "choir_pad"],
        "max_layers": 4
    },
    "combat": {
        "required": ["strings_pad_low", "brass_sustain_mid"],
        "optional": ["strings_tremolo", "perc_soft_pulse"],
        "max_layers": 5
    },
    "boss": {
        "required": ["strings_pad_low", "brass_sustain_low"],
        "optional": ["strings_tremolo", "perc_taiko_low", "choir_pad"],
        "max_layers": 6
    }
}

# =========================
# MUSIC GENERATOR
# =========================

class MusicGenerator:
    def __init__(self):
        self.stems = self._index_stems()

    def _index_stems(self) -> Dict[str, Path]:
        stems = {}
        for wav in STEM_DIR.glob("*.wav"):
            key = wav.name.split("_60bpm")[0]
            stems[key] = wav
        return stems

    # -------------------------
    # PUBLIC API
    # -------------------------

    def get_track(self, context: MusicContext) -> Path:
        profile = self._select_profile(context)
        track_hash = self._hash(context, profile)

        output = TRACK_DIR / f"{track_hash}.ogg"
        if output.exists():
            return output

        self._render_track(profile, context, output)
        return output

    # -------------------------
    # PROFILE SELECTION
    # -------------------------

    def _select_profile(self, context: MusicContext) -> Dict:
        if context.danger > 0.8:
            return TRACK_PROFILES["boss"]
        if context.danger > 0.5:
            return TRACK_PROFILES["combat"]
        if context.danger > 0.25:
            return TRACK_PROFILES["tension"]
        return TRACK_PROFILES["exploration"]

    # -------------------------
    # RENDERING
    # -------------------------

    def _render_track(self, profile: Dict, context: MusicContext, output: Path):
        random.seed(context.seed)

        layers: List[str] = list(profile["required"])
        optional = profile["optional"].copy()
        random.shuffle(optional)

        while len(layers) < profile["max_layers"] and optional:
            layers.append(optional.pop())

        mix: Optional[AudioSegment] = None

        for name in layers:
            stem = self.stems.get(name)
            if not stem:
                continue

            audio = AudioSegment.from_file(stem)
            audio = audio - 6  # headroom

            mix = audio if mix is None else mix.overlay(audio)

        mix.export(output, format="ogg")

    # -------------------------
    # UTILS
    # -------------------------

    def _hash(self, context: MusicContext, profile: Dict) -> str:
        raw = json.dumps({
            "context": context.__dict__,
            "profile": profile
        }, sort_keys=True)

        return hashlib.sha256(raw.encode()).hexdigest()
