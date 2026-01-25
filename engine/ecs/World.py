from collections import defaultdict


class World:
    def __init__(self):
        self._Entities = set()
        self._Components = defaultdict(dict)  # {ComponentType: {entityId: component}}
        self._Systems = []

    # -------------------
    # Entity Management
    # -------------------

    def CreateEntity(self):
        from engine.ecs.Entity import Entity
        entity = Entity()
        self._Entities.add(entity.Id)
        return entity

    def DestroyEntity(self, entity):
        if entity.Id in self._Entities:
            self._Entities.remove(entity.Id)

        for compDict in self._Components.values():
            compDict.pop(entity.Id, None)

    # -------------------
    # Component Management
    # -------------------

    def AddComponent(self, entity, component):
        self._Components[type(component)][entity.Id] = component

    def RemoveComponent(self, entity, componentType):
        self._Components[componentType].pop(entity.Id, None)

    def GetComponent(self, entity, componentType):
        return self._Components[componentType].get(entity.Id)

    # -------------------
    # Queries
    # -------------------

    def Query(self, *componentTypes):
        if not componentTypes:
            return []

        first = self._Components[componentTypes[0]]

        result = []
        for entityId in first:
            if all(entityId in self._Components[ct] for ct in componentTypes):
                result.append(entityId)

        return result

    # -------------------
    # Systems
    # -------------------

    def AddSystem(self, system):
        self._Systems.append(system)

    def Update(self):
        for system in self._Systems:
            system.Update(self)

    def FixedUpdate(self):
        for system in self._Systems:
            system.FixedUpdate(self)
