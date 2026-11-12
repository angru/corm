import pytest

from corm import AccessMode, Entity, Field, KeyNested, Nested, Relationship, Storage


@pytest.fixture(params=[Nested, KeyNested])
def models(request):
    class Target(Entity):
        id: int = Field(pk=True)
        owners: list["Owner"] = Relationship()
        owner: "ExclusiveOwner | None" = Relationship()

    def relation(back, **options):
        kind = request.param
        return kind(
            Target if kind is Nested else Target.id, back_populates=back, **options
        )

    class Owner(Entity):
        targets: list[Target] = relation("owners")

    class ExclusiveOwner(Entity):
        targets: list[Target] = relation("owner", mode=AccessMode.ALL, default=list)

    return Target, Owner, ExclusiveOwner


@pytest.mark.parametrize("reverse", [False, True], ids=["owning", "reverse"])
def test_single_edits_use_incremental_updates(models, reverse, monkeypatch):
    Target, Owner, _ = models
    storage = Storage()
    first, second = [Target({"id": i}, storage) for i in range(2)]
    one, two = [Owner({"targets": []}, storage) for _ in range(2)]
    view, items = (
        (first.owners, [one, two]) if reverse else (one.targets, [first, second])
    )

    def whole_list_write(*args, **kwargs):
        pytest.fail("a single edit rewrote the owning list")

    with monkeypatch.context() as patch:
        patch.setattr(Owner.targets, "_replace_paired_data", whole_list_write)
        view.append(items[0])
        view.append(items[1])
        view.remove(items[0])

    assert view == items[1:]
    assert first.owners == ([two] if reverse else [])
    assert one.targets == ([] if reverse else [second])


@pytest.mark.parametrize("reverse", [False, True], ids=["owning", "reverse"])
def test_single_edits_preserve_snapshots_and_fail_atomically(models, reverse):
    Target, Owner, _ = models
    storage = Storage()
    first, second = [Target({"id": i}, storage) for i in range(2)]
    one, two = [Owner({"targets": []}, storage) for _ in range(2)]
    foreign_target = Target({"id": 1}, Storage())
    foreign_owner = Owner({"targets": []}, foreign_target.storage)
    if reverse:
        read = lambda: first.owners  # noqa: E731
        items, foreign = [one, two], foreign_owner
    else:
        read = lambda: one.targets  # noqa: E731
        items, foreign = [first, second], foreign_target
    stale, view = read(), read()
    assert stale is not view
    view.append(items[0])
    assert stale == []

    with pytest.raises(ValueError, match="same storage"):
        stale.append(foreign)
    assert stale == []
    assert view == read() == items[:1]

    if reverse:
        stale.append(items[0])
        assert stale == items[:1]
    else:
        with pytest.raises(ValueError, match="Duplicate entities"):
            stale.append(items[0])
        assert stale == []

    stale.append(items[1])
    assert stale == read() == items
    assert view == items[:1]
    view.remove(items[1])
    assert view == read() == items[:1]
    assert stale == items


def test_move_by_append_preserves_other_targets_and_old_view(models):
    Target, _, Owner = models
    storage = Storage()
    first, moving, last = [Target({"id": i}, storage) for i in range(3)]
    old, new = [Owner({}, storage) for _ in range(2)]
    old.targets = [first, moving, last]
    snapshot = old.targets
    destination = new.targets

    destination.append(moving)

    assert destination == new.targets == [moving]
    assert moving.owner is new
    assert first.owner is last.owner is old
    assert old.targets == [first, last]
    assert snapshot == [first, moving, last]


def test_key_append_refreshes_after_pending_key_resolves():
    class Target(Entity):
        id: int = Field(pk=True)
        owners: list["Owner"] = Relationship()

    class Owner(Entity):
        targets: list[Target] = KeyNested(
            Target.id, back_populates="owners", required=False
        )

    storage = Storage()
    first = Target({"id": 1}, storage)
    owner = Owner({"targets": [1, 2]}, storage)
    old_dump = owner.dict()
    view = owner.targets

    pending = Target({"id": 2}, storage)
    last = Target({"id": 3}, storage)
    assert view == [first]
    view.append(last)

    assert view == owner.targets == [first, pending, last]
    assert pending.owners == last.owners == [owner]
    assert owner.dict() == {"targets": [1, 2, 3]}
    assert old_dump == {"targets": [1, 2]}
