import requests
import numpy as np
import soundfile as sf
from pathlib import Path
import hashlib
import os

HF_TOKEN = os.getenv('HF_TOKEN')

API_URL = "https://router.huggingface.co/hf-inference/models/facebook/musicgen-small"
r = requests.get(
    "https://router.huggingface.co/hf-inference/models/facebook/musicgen-small",
    headers={"Authorization": f"Bearer {HF_TOKEN}"}
)
print(r.status_code)
print(r.text[:300])

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

SAMPLE_RATE = 32000

def debug(msg: str):
    print(f"[MusicAPI] {msg}")

def build_prompt(ctx: dict) -> str:
    parts = [
        "dark fantasy orchestral music",
        "cinematic",
        "ambient",
        "no vocals"
    ]

    biome_map = {
        "ashlands": "volcanic wasteland",
        "forest": "mystical forest",
        "ruins": "ancient ruins",
    }

    mood_map = {
        "exploration": "slow evolving atmosphere",
        "combat": "intense rhythmic tension",
        "boss": "epic dramatic confrontation",
    }

    parts.append(biome_map.get(ctx["biome"], ctx["biome"]))
    parts.append(mood_map.get(ctx["mood"], ctx["mood"]))

    if ctx.get("danger", 0) > 0.6:
        parts.append("dark aggressive tone")

    prompt = ", ".join(parts)
    debug(f"Built prompt: {prompt}")
    return prompt

def generate_music(ctx: dict, out_path: Path, seconds=15):
    prompt = build_prompt(ctx)

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": seconds * 50
        }
    }

    debug("Calling Hugging Face MusicGen API…")
    r = requests.post(API_URL, headers=HEADERS, json=payload)

    if r.status_code != 200:
        debug(f"API ERROR {r.status_code}: {r.text}")
        raise RuntimeError("MusicGen API failed")

    audio = np.frombuffer(r.content, dtype=np.int16)
    audio = audio.astype(np.float32) / 32768.0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(out_path, audio, SAMPLE_RATE)

    debug(f"Saved audio → {out_path}")
    return out_path

def hash_prompt(prompt: str) -> str:
    return hashlib.sha1(prompt.encode()).hexdigest()
