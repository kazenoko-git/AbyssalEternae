import time


class Time:
    Delta = 0.0
    Total = 0.0

    _LastFrameTime = time.perf_counter()

    @classmethod
    def Update(cls):
        now = time.perf_counter()
        cls.Delta = now - cls._LastFrameTime
        cls.Total += cls.Delta
        cls._LastFrameTime = now
