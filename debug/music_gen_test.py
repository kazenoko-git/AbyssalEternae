from game.ai.music.musicGen import MusicGenerator, MusicContext

print("=== MUSIC GEN TEST START ===")

mg = MusicGenerator()

ctx = MusicContext(
    biome="ashlands",
    mood="exploration",
    danger=0.2
)

print("Requesting track…")
track = mg.get_track(ctx)

print("Returned path:", track)
print("File exists:", track.exists())
print("File size:", track.stat().st_size if track.exists() else "N/A")

print("=== MUSIC GEN TEST END ===")
