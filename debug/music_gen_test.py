from game.ai.music.musicGen import MusicGenerator, MusicContext

mg = MusicGenerator()

ctx = MusicContext(
    biome="Ashlands",
    situation="exploration",
    intensity="low"
)

track = mg.get_track(ctx)
print("Generated:", track)
