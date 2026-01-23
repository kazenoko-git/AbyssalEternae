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

# =========================
# PATHS (ROBUST)
# =========================

# =========================
# PATHS (BULLETPROOF)
# =========================

from pathlib import Path

def find_project_root(marker: str) -> Path:
    p = Path(__file__).resolve()
    while p != p.parent:
        if p.name == marker:
            return p
        p = p.parent
    raise RuntimeError(f"Project root '{marker}' not found")

PROJECT_ROOT = find_project_root("Rifted")
GAME_DIR = PROJECT_ROOT / "game"

MUSIC_DIR = GAME_DIR / "audio" / "music"
STEM_DIR = MUSIC_DIR / "stems"
TRACK_DIR = MUSIC_DIR / "generated" / "tracks"
DEBUG_DIR = MUSIC_DIR / "generated" / "debug"

TRACK_DIR.mkdir(parents=True, exist_ok=True)
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# DEBUG UTIL
# =========================

def debug(msg: str):
    print(f"[MusicGen] {msg}")

# =========================
# DATA MODELS
# =========================

@dataclass(frozen=True)
class MusicContext:
    biome: str
    danger: float          # 0.0 – 1.0
    narrative: str
    dimension: str
    seed: int
    boss_phase: int = 0    # 0 = not boss, 1–3 = boss phases

# =========================
# TRACK PROFILES
# =========================

TRACK_PROFILES: Dict[str, Dict] = {
    "exploration": {
        "required": ["strings_pad_mid", "choir_airy"],
        "optional": ["piano_sparse", "harp_pluck", "strings_pad_high"],
        "base_layers": 2
    },
    "tension": {
        "required": ["strings_pad_low", "strings_pulse"],
        "optional": ["brass_sustain_low", "choir_pad"],
        "base_layers": 3
    },
    "combat": {
        "required": ["strings_pad_low", "brass_sustain_mid"],
        "optional": ["strings_tremolo", "perc_soft_pulse"],
        "base_layers": 4
    },
    "boss": {
        "required": ["strings_pad_low", "brass_sustain_low"],
        "optional": ["strings_tremolo", "perc_taiko_low", "choir_pad"],
        "base_layers": 4
    }
}

# =========================
# MUSIC GENERATOR
# =========================

class MusicGenerator:
    def __init__(self):
        debug("Initializing MusicGenerator")
        self.stems = self._index_stems()

    # -------------------------
    # STEM DISCOVERY
    # -------------------------

    def _index_stems(self) -> Dict[str, Path]:
        debug(f"Scanning stems in: {STEM_DIR.resolve()}")
        stems = {}

        if not STEM_DIR.exists():
            debug("ERROR: Stem directory does not exist!")
            return stems

        for wav in STEM_DIR.glob("*.wav"):
            name = wav.name
            if "_60bpm" not in name:
                debug(f"Skipping non-standard stem: {name}")
                continue

            key = name.split("_60bpm")[0]
            stems[key] = wav
            debug(f"Registered stem: {key} → {wav.name}")

        debug(f"Total stems registered: {len(stems)}")
        debug(f"Available stem keys: {list(stems.keys())}")

        return stems

    # -------------------------
    # PUBLIC API
    # -------------------------

    def get_track(self, context: MusicContext) -> Path:
        profile_name, profile = self._select_profile(context)
        track_hash = self._hash(context, profile_name)

        output = TRACK_DIR / f"{track_hash}.ogg"
        debug(f"Requested track → profile={profile_name}, hash={track_hash[:8]}")

        if output.exists():
            debug("Track cache hit")
            return output

        self._render_track(profile_name, profile, context, output)
        return output

    # -------------------------
    # PROFILE SELECTION (AI-ish)
    # -------------------------

    def _select_profile(self, context: MusicContext):
        # Boss overrides everything
        if context.boss_phase > 0:
            debug(f"Boss phase {context.boss_phase} detected")
            return "boss", TRACK_PROFILES["boss"]

        if context.danger >= 0.6:
            return "combat", TRACK_PROFILES["combat"]
        if context.danger >= 0.3:
            return "tension", TRACK_PROFILES["tension"]
        return "exploration", TRACK_PROFILES["exploration"]

    # -------------------------
    # TRACK RENDERING
    # -------------------------

    def _render_track(self, profile_name: str, profile: Dict,
                      context: MusicContext, output: Path):

        random.seed(context.seed)
        debug(f"Rendering new track: {output.name}")

        layers: List[str] = list(profile["required"])
        optional = profile["optional"].copy()
        random.shuffle(optional)

        # Adaptive intensity
        extra_layers = int(context.danger * 3)

        # Boss escalation
        if profile_name == "boss":
            extra_layers += context.boss_phase

        target_layers = profile["base_layers"] + extra_layers

        debug(f"Target layers: {target_layers}")

        while len(layers) < target_layers and optional:
            layers.append(optional.pop())

        debug(f"Final layers: {layers}")

        mix: Optional[AudioSegment] = None

        for name in layers:
            stem = self.stems.get(name)
            if not stem:
                debug(f"WARNING: Missing stem '{name}'")
                continue

            debug(f"Adding stem: {name}")
            audio = AudioSegment.from_file(stem)
            audio = audio - 6  # headroom
            mix = audio if mix is None else mix.overlay(audio)

        if mix is None:
            raise RuntimeError(
                f"No audio layers mixed.\n"
                f"Requested layers: {layers}\n"
                f"Available stems: {list(self.stems.keys())}"
            )

        mix.export(output, format="ogg")

        # Write debug metadata
        debug_file = DEBUG_DIR / f"{output.stem}.json"
        debug_file.write_text(json.dumps({
            "profile": profile_name,
            "layers": layers,
            "danger": context.danger,
            "boss_phase": context.boss_phase,
            "seed": context.seed
        }, indent=2))

        debug(f"Track written: {output}")
        debug(f"Debug data written: {debug_file}")

    # -------------------------
    # HASHING
    # -------------------------

    def _hash(self, context: MusicContext, profile_name: str) -> str:
        raw = json.dumps({
            "context": context.__dict__,
            "profile": profile_name
        }, sort_keys=True)

        return hashlib.sha256(raw.encode()).hexdigest()
