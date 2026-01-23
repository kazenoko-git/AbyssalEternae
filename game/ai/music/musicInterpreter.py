from pydub import AudioSegment
import random

CROSSFADE_MS = 800

ROLE_MAP = {
    "bed": "strings_pad_low",
    "rhythm": "strings_pulse",
    "accent": "brass_sustain_low"
}

class MusicInterpreter:
    def __init__(self, stem_dir):
        self.stems = {
            f.stem: f for f in stem_dir.glob("*.wav")
        }
        if not self.stems:
            raise RuntimeError("No stems found")

    def render(self, plan: dict) -> AudioSegment:
        bar_ms = int((60 / plan["tempo"]) * 4 * 1000)
        track = AudioSegment.silent(0)

        for sec in plan["sections"]:
            seg_len = sec["bars"] * bar_ms
            seg = AudioSegment.silent(seg_len)

            # --- harmonic layers ---
            for role in sec["roles"]:
                base = ROLE_MAP.get(role)
                if not base:
                    continue

                key = f"{base}_{sec['chord']}"
                if key in self.stems:
                    stem = AudioSegment.from_file(self.stems[key])
                    stem -= (20 - sec["energy"] * 12)
                    seg = seg.overlay(stem[:seg_len])
                    self.used_any_layer = True

            # --- motif (melody) ---
            if sec.get("motif"):
                mkey = f"motif_{sec['motif']}_{sec['chord']}"
                if mkey in self.stems:
                    motif = AudioSegment.from_file(self.stems[mkey]) - 10
                    seg = seg.overlay(motif[:seg_len])
            if not self.used_any_layer:
                raise RuntimeError(
                    f"No stems matched for section: chord={sec['chord']} roles={sec['roles']}"
                )

            # --- crossfade append ---
            if len(track) == 0:
                track = seg
            else:
                track = track.append(seg, crossfade=CROSSFADE_MS)

        return track
