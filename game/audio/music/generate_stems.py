import os
import subprocess
import tempfile
from pathlib import Path

SOUNDFONT = "game/audio/music/soundfonts/orchestra.sf2"
OUTPUT_DIR = "game/audio/music/stems"

BPM = 60
SECONDS_PER_BAR = 4 * 60 / BPM
BARS = 8
DURATION = int(SECONDS_PER_BAR * BARS)

# GM program numbers (1-based in docs, 0-based in fluidsynth)
INSTRUMENTS = {
    "strings_pad": 48,      # String Ensemble
    "brass_low": 61,        # Brass Section
    "choir_pad": 52,        # Choir Aahs
    "percussion_soft": 0    # Percussion handled separately
}

NOTE_MAP = {
    "E_minor": [52, 55, 59]  # E, G, B
}


def render_stem(name, program, notes, velocity=80):
    out_path = Path(OUTPUT_DIR) / f"{name}_60bpm_em.wav"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".sf", delete=False) as sf:
        sf.write(f"""
soundfont "{SOUNDFONT}"
program 0 {program}
gain 0.8
""")
        for note in notes:
            sf.write(f"noteon 0 {note} {velocity}\n")
        sf.write(f"sleep {DURATION}\n")
        for note in notes:
            sf.write(f"noteoff 0 {note}\n")
        sf.write("quit\n")

        sf_path = sf.name

    subprocess.run([
        "fluidsynth",
        "-ni",
        SOUNDFONT,
        sf_path,
        "-F",
        str(out_path),
        "-r",
        "44100"
    ], check=True)

    os.remove(sf_path)
    print(f"Generated: {out_path}")


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    render_stem(
        name="strings_pad",
        program=INSTRUMENTS["strings_pad"],
        notes=NOTE_MAP["E_minor"]
    )

    render_stem(
        name="brass_low",
        program=INSTRUMENTS["brass_low"],
        notes=[40, 43]  # low E + G
    )

    render_stem(
        name="choir_pad",
        program=INSTRUMENTS["choir_pad"],
        notes=NOTE_MAP["E_minor"],
        velocity=60
    )

    # Percussion (simple pulse)
    render_stem(
        name="percussion_soft",
        program=0,
        notes=[36],  # kick
        velocity=50
    )
