import gc
import tracemalloc
from statistics import median

from corm import Entity, Field, KeyNested, Relationship, Storage


class Target(Entity):
    id: int = Field(pk=True)
    owners: list["Owner"] = Relationship()


class Owner(Entity):
    targets: list[Target] = KeyNested(Target.id, back_populates="owners")


def sample(count):
    gc.collect()
    tracemalloc.start()
    store = Storage()
    owners = []
    for i in range(count):
        target = Target({"id": i}, store)
        owner = Owner({"targets": [i]}, store)
        owner.targets.remove(target)
        assert target.owners == []
        target.owners.append(owner)
        assert owner.targets == [target] and target.owners == [owner]
        owners.append(owner)
    gc.collect()
    size = tracemalloc.get_traced_memory()[0]
    tracemalloc.stop()
    return size


if __name__ == "__main__":
    sample(16)
    print(f"Median retained bytes: {median(sample(10_000) for _ in range(3)):,}")
