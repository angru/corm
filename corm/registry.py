from typing import TYPE_CHECKING

from corm.exceptions import RegistryError

if TYPE_CHECKING:
    from corm.entity import Entity

_registry: dict[str, type["Entity"]] = {}


def add(entity_class: type["Entity"], name: str | None = None) -> None:
    if name is None:
        name = f"{entity_class.__module__}.{entity_class.__qualname__}"
    _registry[name] = entity_class


def get(name: str) -> type["Entity"]:
    if name in _registry:
        return _registry[name]

    matches = {
        full_name: entity_class
        for full_name, entity_class in _registry.items()
        if entity_class.__name__ == name
    }
    if len(matches) == 1:
        return next(iter(matches.values()))
    if matches:
        raise RegistryError(
            f"Ambiguous entity name {name!r}; use one of: {', '.join(sorted(matches))}"
        )
    raise RegistryError(f"Unknown entity {name!r}")


def clear() -> None:
    _registry.clear()
