"""Measure appends on one list snapshot in each direction of a paired relation."""

import argparse
import gc
import warnings
from time import perf_counter

from corm import Entity, Field, KeyNested, Nested, Relationship, Storage


class Target(Entity):
    id: int = Field(pk=True)
    nested_owners: list["NestedOwner"] = Relationship()
    key_owners: list["KeyOwner"] = Relationship()


class NestedOwner(Entity):
    targets: list[Target] = Nested(back_populates="nested_owners")


class KeyOwner(Entity):
    targets: list[Target] = KeyNested(Target.id, back_populates="key_owners")


with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)

    class LegacyOwner(Entity):
        targets: list[Target] = Nested(back_relation=True)


def measure(count, owner_type, reverse):
    storage = Storage()
    if reverse:
        target = Target({"id": 0}, storage)
        entities = [owner_type({"targets": []}, storage) for _ in range(count)]
        view = target.key_owners if owner_type is KeyOwner else target.nested_owners
    else:
        owner = owner_type({"targets": []}, storage)
        entities = [Target({"id": i}, storage) for i in range(count)]
        view = owner.targets

    gc.collect()
    start = perf_counter()
    for entity in entities:
        view.append(entity)
    elapsed = perf_counter() - start
    assert view == entities
    if reverse:
        assert all(owner.targets == [target] for owner in entities)
    elif owner_type is not LegacyOwner:
        assert owner.targets == entities
    return elapsed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("counts", type=int, nargs="*", default=[4000, 40000])
    args = parser.parse_args()
    if any(count < 1 for count in args.counts):
        parser.error("counts must be positive")

    for count in args.counts:
        for owner_type in (NestedOwner, KeyOwner, LegacyOwner):
            for reverse in (False, True) if owner_type is not LegacyOwner else (False,):
                direction = "reverse" if reverse else "owning"
                elapsed = measure(count, owner_type, reverse)
                print(
                    f"{count:>6} {owner_type.__name__:12} {direction:7}"
                    f" {elapsed:.6f} s",
                    flush=True,
                )


if __name__ == "__main__":
    main()
