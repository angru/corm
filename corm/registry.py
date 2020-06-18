_registry = {}


def add(entity_class, name: str = None):
    if name and name in _registry:
        raise ValueError(
            f'Entity class with name {name} already in registry. You probably should use full path to entity class '
            f'e.g. {entity_class.__module__}.{entity_class.__name__}'
        )

    if name is None:
        add(entity_class, entity_class.__name__)
        add(entity_class, f'{entity_class.__module__}.{entity_class.__name__}')
    else:
        _registry[name] = entity_class


def get(name: str):
    return _registry[name]


def clear():
    _registry.clear()
