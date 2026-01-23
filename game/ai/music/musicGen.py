import hashlib, json
from pathlib import Path
from dataclasses import dataclass

from .musicPlanGen import MusicPlanGenerator
from .musicInterpreter import MusicInterpreter
from .musicDB import MusicDB

def find_root(name="Rifted"):
    p = Path(__file__).resolve()
    while p != p.parent:
        if p.name == name:
            return p
        p = p.parent
    raise RuntimeError("Root not found")

ROOT = find_root()
STEM_DIR = ROOT / "game/audio/music/stems"
OUT_DIR = ROOT / "game/audio/music/generated/tracks"
OUT_DIR.mkdir(parents=True, exist_ok=True)

@dataclass(frozen=True)
class MusicContext:
    biome: str
    situation: str
    intensity: str

class MusicGenerator:
    def __init__(self):
        self.db = MusicDB()
        self.ai = MusicPlanGenerator()
        self.renderer = MusicInterpreter(STEM_DIR)

    def get_track(self, ctx: MusicContext) -> Path:
        key = hashlib.sha256(
            json.dumps(ctx.__dict__, sort_keys=True).encode()
        ).hexdigest()

        cached = self.db.get(key)
        if cached:
            return Path(cached[1])

        plan = self.ai.generate(ctx.__dict__)
        audio = self.renderer.render(plan)

        path = OUT_DIR / f"{key}.ogg"
        audio.export(path, format="ogg")

        self.db.save(key, json.dumps(plan), path)
        return path
