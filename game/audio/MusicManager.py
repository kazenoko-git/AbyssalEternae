from core.GameState import GameState


class MusicManager:

    def __init__(self):
        self.CurrentTrack = None

    def Update(self):

        if GameState.InCombat:
            DesiredMood = "combat"
        elif GameState.InCity:
            DesiredMood = "city"
        else:
            DesiredMood = "exploration"

        if DesiredMood != self.CurrentTrack:
            self.PlayTrack(DesiredMood)

    def PlayTrack(self, Mood):

        print(f"[MusicManager] Switching music to: {Mood}")

        # Later:
        # - Query SQLite
        # - Pick best matching track
        # - Crossfade via Ursina Audio

        self.CurrentTrack = Mood
