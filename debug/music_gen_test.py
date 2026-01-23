from game.ai.musicGen import MusicGenerator, MusicContext

mg = MusicGenerator()

ctx = MusicContext(
    biome="Ashlands",
    danger=0.7,
    narrative="grim",
    dimension="fractured",
    seed=12345,
    boss_phase=2
)

track = mg.get_track(ctx)
print("Generated track:", track)
