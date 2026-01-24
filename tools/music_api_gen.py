import requests
import soundfile as sf
import numpy as np
from pathlib import Path
import json
import hashlib
import os

HF_TOKEN = os.getenv("HF_TOKEN")

API_URL = "https://api-inference.huggingface.co/models/facebook/musicgen-small"
HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Accept": "audio/wav"
}

OUT_BASE = Path("game/audio/music")
OUT_BASE.mkdir(parents=True, exist_ok=True)

def build_prompt(tags: dict) -> str:
    parts = [
        "dark fantasy orchestral music",
        "cinematic",
        "ambient",
        "no vocals"
    ]

    biome_map = {
        "ashlands": "volcanic wasteland",
        "forest": "mystical forest",
        "ruins": "ancient ruins"
    }

    mood_map = {
        "exploration": "slow evolving atmosphere",
        "combat": "intense rhythmic tension",
        "boss": "epic dramatic confrontation"
    }

    parts.append(biome_map.get(tags["biome"], tags["biome"]))
    parts.append(mood_map.get(tags["mood"], tags["mood"]))

    if tags.get("danger") == "high":
        parts.append("dark aggressive tone")

    return ", ".join(parts)

def generate_music(tags: dict, seconds=15):
    prompt = build_prompt(tags)

    print("[Music API] Prompt:", prompt)

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": seconds * 50
        }
    }

    r = requests.post(API_URL, headers=HEADERS, json=payload)
    if r.status_code != 200:
        raise RuntimeError(r.text)

    audio = np.frombuffer(r.content, dtype=np.int16)
    audio = audio.astype(np.float32) / 32768.0

    h = hashlib.sha1(prompt.encode()).hexdigest()[:10]
    out_dir = OUT_BASE / tags["mood"]
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"{tags['biome']}_{h}.wav"
    sf.write(out_path, audio, 32000)

    print("Saved:", out_path)
    return out_path


if __name__ == "__main__":
    generate_music({
        "biome": "ashlands",
        "mood": "exploration",
        "danger": "low"
    })
