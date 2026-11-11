"""Measure loading entities that share a KeyNested back relation."""

import argparse
import gc
from time import perf_counter

from corm import Entity, Field, KeyNested, RelationType, Storage


class Target(Entity):
    id: int = Field(pk=True)


class Holder(Entity):
    target = KeyNested(Target.id, origin="target_id", back_relation=True)


def measure(count: int) -> float:
    storage = Storage()
    target = Target({"id": 1}, storage)
    gc.collect()

    start = perf_counter()
    for _ in range(count):
        last = Holder({"target_id": 1}, storage)
    elapsed = perf_counter() - start

    related = storage.get_related_entities(target, Holder, RelationType.RELATED)
    assert len(related) == count and related[-1] is last
    return elapsed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "counts", metavar="COUNT", type=int, nargs="*", default=[8000, 80000]
    )
    args = parser.parse_args()
    if any(count < 1 for count in args.counts):
        parser.error("counts must be positive")

    for count in args.counts:
        print(f"{count:>7,} entities: {measure(count):.6f} s", flush=True)


if __name__ == "__main__":
    main()
