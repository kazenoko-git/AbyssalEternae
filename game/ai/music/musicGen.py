import json
import hashlib
from pathlib import Path
from dataclasses import dataclass

from .musicDB import MusicDB
from .musicApiGen import generate_music, build_prompt, hash_prompt

def debug(msg: str):
    print(f"[MusicGen] {msg}")

def find_root(marker="Rifted") -> Path:
    p = Path(__file__).resolve()
    while p != p.parent:
        if p.name == marker:
            return p
        p = p.parent
    raise RuntimeError("Project root not found")

ROOT = find_root()
OUT_DIR = ROOT / "game/audio/music/generated/tracks"
OUT_DIR.mkdir(parents=True, exist_ok=True)

@dataclass(frozen=True)
class MusicContext:
    biome: str
    mood: str
    danger: float = 0.0

class MusicGenerator:
    def __init__(self):
        debug("Initializing MusicGenerator (API mode)")
        self.db = MusicDB()

    def get_track(self, ctx: MusicContext) -> Path:
        ctx_dict = ctx.__dict__
        prompt = build_prompt(ctx_dict)
        key = hash_prompt(prompt)

        debug(f"Request track | key={key}")

        cached = self.db.get(key)
        if cached:
            path = Path(cached[1])
            debug(f"CACHE HIT → {path}")
            return path

        debug("CACHE MISS → generating via API")
        out_path = OUT_DIR / f"{key}.wav"

        generate_music(ctx_dict, out_path)

        self.db.save(key, json.dumps(ctx_dict), out_path)
        debug("Track cached successfully")

        return out_path
