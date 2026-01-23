from pathlib import Path
import numpy as np
import soundfile as sf
import fluidsynth

# =========================
# PATHS
# =========================

BASE = Path(__file__).resolve().parent
STEM_DIR = BASE / "stems"
SOUNDFONT = BASE / "soundfonts" / "arachno.sf2"

STEM_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# AUDIO CONFIG
# =========================

SAMPLE_RATE = 44100
BPM = 60
BARS = 8
SECONDS = (60 / BPM) * 4 * BARS
FRAMES = int(SECONDS * SAMPLE_RATE)

# =========================
# MUSICAL DATA
# =========================

CHORDS = {
    "Em": [52, 55, 59],
    "C":  [48, 52, 55],
    "G":  [55, 59, 62],
    "D":  [50, 54, 57],
}

LOW = {
    "Em": [40, 43],
    "C":  [36, 40],
    "G":  [43, 47],
    "D":  [38, 42],
}

HIGH = {
    "Em": [64, 67, 71],
    "C":  [60, 64, 67],
    "G":  [67, 71, 74],
    "D":  [62, 66, 69],
}

# Simple melodic motifs (1–2 bars feel)
MOTIFS = {
    "melancholy": lambda chord: [chord[0], chord[1], chord[2], chord[1]],
    "heroic":     lambda chord: [chord[0], chord[2], chord[1], chord[2]],
}

GM = {
    "strings": 48,
    "tremolo": 44,
    "brass": 61,
    "horns": 60,
    "choir": 52,
    "piano": 0,
    "harp": 46,
}

# =========================
# RENDER FUNCTION
# =========================

def render_stem(name, notes, program, velocity=70, percussion=False):
    fs = fluidsynth.Synth(samplerate=SAMPLE_RATE)
    fs.set_reverb(False)
    fs.set_chorus(False)

    sfid = fs.sfload(str(SOUNDFONT))
    if sfid == -1:
        raise RuntimeError(f"SoundFont failed to load: {SOUNDFONT}")

    channel = 9 if percussion else 0
    fs.program_select(channel, sfid, 0, program)

    audio = np.zeros((FRAMES, 2), dtype=np.float32)

    for note in notes:
        fs.noteon(channel, note, velocity)

    idx = 0
    chunk = 1024
    while idx < FRAMES:
        n = min(chunk, FRAMES - idx)
        audio[idx:idx+n] = fs.get_samples(n).reshape(-1, 2)
        idx += n

    for note in notes:
        fs.noteoff(channel, note)

    fs.delete()

    # Fade in/out
    fade_len = int(0.5 * SAMPLE_RATE)
    fade = np.linspace(0, 1, fade_len)
    audio[:fade_len] *= fade[:, None]
    audio[-fade_len:] *= fade[::-1][:, None]

    # Normalize
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio *= 0.8 / peak

    sf.write(STEM_DIR / name, audio, SAMPLE_RATE)
    print(f"Generated: {name}")

# =========================
# GENERATE ALL STEMS
# =========================

if __name__ == "__main__":

    for chord, notes in CHORDS.items():
        print(f"\n=== Generating stems for {chord} ===")

        # Pads
        render_stem(f"strings_pad_low_{chord}.wav", LOW[chord], GM["strings"])
        render_stem(f"strings_pad_mid_{chord}.wav", notes, GM["strings"])
        render_stem(f"strings_pad_high_{chord}.wav", HIGH[chord], GM["strings"])
        render_stem(f"choir_pad_{chord}.wav", notes, GM["choir"])

        # Motion
        render_stem(f"strings_tremolo_{chord}.wav", notes, GM["tremolo"], velocity=60)
        render_stem(f"strings_pulse_{chord}.wav", notes, GM["strings"], velocity=55)
        render_stem(f"choir_airy_{chord}.wav", notes, GM["choir"], velocity=45)

        # Brass
        render_stem(f"brass_sustain_low_{chord}.wav", LOW[chord], GM["brass"])
        render_stem(f"horns_warm_{chord}.wav", notes, GM["horns"])

        # Piano / Harp
        render_stem(f"piano_sparse_{chord}.wav", notes, GM["piano"], velocity=45)
        render_stem(f"harp_pluck_{chord}.wav", notes, GM["harp"], velocity=60)

        # Motifs (MELODY)
        for motif, fn in MOTIFS.items():
            motif_notes = fn(notes)
            render_stem(
                f"motif_{motif}_{chord}.wav",
                motif_notes,
                GM["strings"],
                velocity=70
            )

    # Percussion (unchorded)
    render_stem("perc_soft_pulse.wav", [36], 0, percussion=True)
    render_stem("perc_taiko_low.wav", [35], 0, percussion=True)
    render_stem("perc_ticks_high.wav", [42], 0, percussion=True)
