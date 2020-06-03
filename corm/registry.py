_registry = {}


def add(model_class, name: str = None):
    if name and name in _registry:
        raise ValueError(
            f'Model class with name {name} already in registry. You probably should use full path to model '
            f'e.g. {model_class.__module__}.{model_class.__name__}'
        )

    if name is None:
        add(model_class, model_class.__name__)
        add(model_class, f'{model_class.__module__}.{model_class.__name__}')
    else:
        _registry[name] = model_class


def get(name: str):
    return _registry[name]


def clear():
    _registry.clear()
