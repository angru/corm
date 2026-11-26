"""Compare a document scan, two keyed scan predicates and a primary-key lookup."""

import gc
import platform
import weakref
from collections.abc import Iterator
from statistics import median
from timeit import repeat

from corm import Entity, Field, Storage


class User(Entity):
    name: str


class Member(User):
    id: int = Field(pk=True)


class Contact(User):
    id: int = Field(pk=True)
    alias: int = Field(pk=True)


def indexed_users(store: Storage) -> Iterator[User]:
    # Research prototype. The private index has one entry per primary key.
    seen: set[int] = set()
    for entity in store._entities.values():
        if isinstance(entity, User) and id(entity) not in seen:
            seen.add(id(entity))
            yield entity


def field_equals(name, value):
    return lambda entity: getattr(entity, name) == value


def measure(label, lookup, expected):
    assert lookup() is expected
    calls = 20
    seconds = median(repeat(lookup, repeat=5, number=calls)) / calls
    print(f"  {label:<22} {seconds * 1_000_000:10.2f} us")


def measure_lookups(users, store, model, keys):
    count = len(users)
    target = str(count - 1)
    expected = users[-1] if keys else None
    print(f"{model.__name__}: {len(users)} users, {len(store._entities)} key entries")
    assert len(store._entities) == count * len(keys)
    assert list(indexed_users(store)) == (users if keys else [])
    assert (User.name == target) is False

    measure(
        "Collection generator",
        lambda: next((user for user in users if user.name == target), None),
        users[-1],
    )
    measure(
        "Keyed generator",
        lambda: next(
            (user for user in indexed_users(store) if user.name == target), None
        ),
        expected,
    )
    predicate = field_equals("name", target)
    measure(
        "Keyed field equality",
        lambda: next(filter(predicate, indexed_users(store)), None),
        expected,
    )
    for key in keys:
        field = getattr(model, key)
        measure(
            f"Storage.get({key})",
            lambda field=field: store.get(field, count - 1),
            expected,
        )


def run_case(model, keys, count):
    store = Storage()
    users = [
        model({"name": str(i), **dict.fromkeys(keys, i)}, store) for i in range(count)
    ]
    measure_lookups(users, store, model, keys)
    refs = [weakref.ref(user) for user in users]
    del users
    gc.collect()
    retained = sum(ref() is not None for ref in refs)
    print(f"  Retained with store alive: {retained}")
    assert retained == (count if keys else 0)
    del store
    gc.collect()
    assert all(ref() is None for ref in refs)


if __name__ == "__main__":
    print(f"{platform.python_implementation()} {platform.python_version()}")
    for model, keys in ((User, ()), (Member, ("id",)), (Contact, ("id", "alias"))):
        run_case(model, keys, 10_000)
