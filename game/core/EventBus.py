class EventBus:
    _Queue = []

    @classmethod
    def Emit(cls, Event):
        cls._Queue.append(Event)

    @classmethod
    def Process(cls):
        while cls._Queue:
            Event = cls._Queue.pop(0)
            try:
                Event.Handle()
            except Exception as e:
                print(f"[EventBus] Error handling event: {e}")
