from pathlib import Path
import numpy as np
import soundfile as sf
import fluidsynth

# =========================
# PATHS
# =========================

BASE = Path(__file__).resolve().parent
STEM_DIR = BASE / "stems"
SOUNDFONT = BASE / "soundfonts" / "FluidR3_GM.sf2"

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

CHORD_E_MINOR = [52, 55, 59]
LOW_E_MINOR = [40, 43]
HIGH_E_MINOR = [64, 67, 71]

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
    fs.set_gain(0.3)

    sfid = fs.sfload(str(SOUNDFONT))
    if sfid == -1:
        raise RuntimeError(f"SoundFont failed to load: {SOUNDFONT}")

    channel = 9 if percussion else 0
    fs.program_select(channel, sfid, 0, program)

    for note in notes:
        fs.noteon(channel, note, velocity)

    audio = np.zeros((FRAMES, 2), dtype=np.float32)

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

    out = STEM_DIR / f"{name}_60bpm_em.wav"
    sf.write(out, audio, SAMPLE_RATE)
    print(f"Generated: {out.name}")


# =========================
# GENERATE ALL STEMS
# =========================

if __name__ == "__main__":

    # Pads
    render_stem("strings_pad_low", LOW_E_MINOR, GM["strings"])
    render_stem("strings_pad_mid", CHORD_E_MINOR, GM["strings"])
    render_stem("strings_pad_high", HIGH_E_MINOR, GM["strings"])
    render_stem("choir_pad", CHORD_E_MINOR, GM["choir"])

    # Motion
    render_stem("strings_tremolo", CHORD_E_MINOR, GM["tremolo"])
    render_stem("strings_pulse", CHORD_E_MINOR, GM["strings"], velocity=60)
    render_stem("choir_airy", CHORD_E_MINOR, GM["choir"], velocity=50)

    # Brass
    render_stem("brass_sustain_low", LOW_E_MINOR, GM["brass"])
    render_stem("brass_sustain_mid", CHORD_E_MINOR, GM["brass"])
    render_stem("horns_warm", CHORD_E_MINOR, GM["horns"])

    # Piano / Harp
    render_stem("piano_low", LOW_E_MINOR, GM["piano"], velocity=55)
    render_stem("piano_sparse", CHORD_E_MINOR, GM["piano"], velocity=45)
    render_stem("harp_pluck", CHORD_E_MINOR, GM["harp"], velocity=60)

    # Percussion
    render_stem("perc_soft_pulse", [36], 0, percussion=True)
    render_stem("perc_taiko_low", [35], 0, percussion=True)
    render_stem("perc_ticks_high", [42], 0, percussion=True)
