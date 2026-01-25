class Entity:
    __NextId = 0

    def __init__(self):
        self.Id = Entity.__NextId
        Entity.__NextId += 1

    def __repr__(self):
        return f"<Entity {self.Id}>"
