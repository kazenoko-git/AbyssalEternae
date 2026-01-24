class Scheduler:
    _Tasks = []

    @classmethod
    def Add(cls, Task):
        cls._Tasks.append(Task)

    @classmethod
    def Run(cls):
        for Task in cls._Tasks.copy():
            try:
                Task()
            except Exception as e:
                print(f"[Scheduler] Task error: {e}")

            cls._Tasks.remove(Task)

