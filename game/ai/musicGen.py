import os
import json
import hashlib
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from pydub import AudioSegment
import random

DB_PATH = "game/db/rifted.db"
STEM_DIR = "game/audio/music/stems"
OUTPUT_DIR = "game/audio/music/generated"

BASE_BPM = 60
TRACK_BARS = 8  # loop length


@dataclass(frozen=True)
class MusicContext:
    biome: str
    dimension_theme: str
    narrative_tone: str
    danger_level: float
    player_state: str
    seed: int


class MusicGenerator:
    def __init__(self):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        self._init_db()

    # ---------------- DB ----------------

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS music_tracks (
            context_hash TEXT PRIMARY KEY,
            audio_path TEXT,
            metadata TEXT,
            created_at TEXT
        )
        """)
        conn.commit()
        conn.close()

    # ------------- PUBLIC API -------------

    def request_music(self, context: MusicContext) -> Optional[str]:
        context_hash = self._hash_context(context)

        cached = self._fetch(context_hash)
        if cached:
            return cached

        threading.Thread(
            target=self._generate_track,
            args=(context, context_hash),
            daemon=True
        ).start()

        return None  # fallback music should play

    # ------------- GENERATION -------------

    def _generate_track(self, context: MusicContext, context_hash: str):
        random.seed(context.seed)

        layers = self._select_layers(context)
        track = self._mix_layers(layers)

        output_path = os.path.join(OUTPUT_DIR, f"{context_hash}.ogg")
        track.export(output_path, format="ogg")

        self._store(context_hash, output_path, layers)

    # ------------- LAYERS -------------

    def _select_layers(self, context: MusicContext) -> List[str]:
        """
        AI-replaceable logic.
        Currently rule-based but GOOD.
        """
        available = os.listdir(STEM_DIR)

        layers = []

        # Always pad
        layers.append(self._pick(available, "strings"))

        if context.danger_level > 0.3:
            layers.append(self._pick(available, "brass"))

        if context.narrative_tone in ("grim", "ancient"):
            layers.append(self._pick(available, "choir"))

        if context.danger_level > 0.6:
            layers.append(self._pick(available, "percussion"))

        return layers

    def _pick(self, files, keyword):
        choices = [f for f in files if keyword in f]
        return os.path.join(STEM_DIR, random.choice(choices))

    # ------------- MIXING -------------

    def _mix_layers(self, layers: List[str]) -> AudioSegment:
        base = None

        for path in layers:
            audio = AudioSegment.from_file(path)

            if base is None:
                base = audio
            else:
                base = base.overlay(audio)

        # Force exact loop length
        loop_length_ms = int((TRACK_BARS * 4 * 60 / BASE_BPM) * 1000)
        base = base[:loop_length_ms]

        return base

    # ------------- CACHE -------------

    def _store(self, context_hash, path, layers):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
        INSERT OR REPLACE INTO music_tracks
        VALUES (?, ?, ?, ?)
        """, (
            context_hash,
            path,
            json.dumps({"layers": layers}),
            datetime.utcnow().isoformat()
        ))
        conn.commit()
        conn.close()

    def _fetch(self, context_hash) -> Optional[str]:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT audio_path FROM music_tracks WHERE context_hash = ?",
            (context_hash,)
        )
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None

    # ------------- UTILS -------------

    def _hash_context(self, context: MusicContext) -> str:
        raw = json.dumps(context.__dict__, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()
