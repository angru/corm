import pytest

from corm import (
    AccessMode,
    Entity,
    Field,
    KeyManager,
    KeyNested,
    Nested,
    Relationship,
    RelationType,
    Storage,
)


@pytest.fixture(params=[Nested, KeyNested], ids=["nested", "key-nested"])
def models(request):
    def make_models(*, owner_many, back_many):
        class Target(Entity):
            id: int = Field(pk=True)
            owners = Relationship("Owner", many=back_many)

        if request.param is KeyNested:
            field = KeyNested(
                Target.id,
                many=owner_many,
                origin="target_ids",
                back_populates="owners",
            )
        else:
            field = Nested(Target, many=owner_many, back_populates="owners")

        class Owner(Entity):
            targets = field

        def check(owner, *targets):
            if owner_many:
                assert owner.targets == list(targets)
                keys = [target.id for target in targets]
            else:
                assert owner.targets is (targets[0] if targets else None)
                keys = targets[0].id if targets else None
            if request.param is KeyNested:
                assert owner.dict() == {"target_ids": keys}

        def make_owner(storage, *ids, owner_type=Owner):
            values = list(ids)
            if request.param is Nested:
                values = [{"id": key} for key in values]
            else:
                for key in values:
                    if storage.get(Target.id, key) is None:
                        Target({"id": key}, storage)
            data = values if owner_many else (values[0] if values else None)
            return owner_type({field.origin: data}, storage)

        return Target, make_owner, check

    return make_models


@pytest.mark.parametrize("owner_many", [False, True], ids=["single", "many"])
def test_single_back_assignment(models, owner_many):
    Target, make_owner, check = models(owner_many=owner_many, back_many=False)
    storage = Storage()
    old_owner = make_owner(storage, 1)
    new_owner = make_owner(storage, 2)
    first, second = (storage.get(Target.id, key) for key in (1, 2))
    assert first.owners is old_owner
    assert second.owners is new_owner

    first.owners = new_owner

    check(old_owner)
    check(new_owner, *((second, first) if owner_many else (first,)))
    assert first.owners is new_owner
    assert second.owners is (new_owner if owner_many else None)

    first.owners = None

    assert first.owners is None
    check(new_owner, *((second,) if owner_many else ()))


@pytest.mark.parametrize("owner_many", [False, True], ids=["single", "many"])
def test_single_back_moves_between_base_and_sibling_owners(models, owner_many):
    Target, make_owner, check = models(owner_many=owner_many, back_many=False)
    storage = Storage()
    original = make_owner(storage, 1)
    target = storage.get(Target.id, 1)
    Owner = type(original)

    class FirstOwner(Owner):
        pass

    class SecondOwner(Owner):
        pass

    first = make_owner(storage, owner_type=FirstOwner)
    second = make_owner(storage, owner_type=SecondOwner)
    base = make_owner(storage, 2)
    displaced = storage.get(Target.id, 2)

    assert target.owners is original
    assert displaced.owners is base

    if owner_many:
        first.targets.append(target)
    else:
        first.targets = target
    check(original)
    check(first, target)
    assert target.owners is first

    target.owners = second
    check(first)
    check(second, target)
    assert target.owners is second

    base.targets = [target] if owner_many else target
    check(second)
    check(base, target)
    assert target.owners is base
    assert displaced.owners is None


def test_many_back_keeps_base_and_sibling_owners(models):
    Target, make_owner, check = models(owner_many=False, back_many=True)
    storage = Storage()
    base = make_owner(storage, 1)
    target = storage.get(Target.id, 1)
    Owner = type(base)

    class FirstOwner(Owner):
        pass

    class SecondOwner(Owner):
        pass

    first = make_owner(storage, owner_type=FirstOwner)
    second = make_owner(storage, owner_type=SecondOwner)
    assert target.owners == [base]

    first.targets = target
    target.owners.append(second)
    assert target.owners == [base, first, second]
    check(first, target)
    check(second, target)

    target.owners = [second, base]
    assert target.owners == [second, base]
    check(base, target)
    check(first)
    check(second, target)


@pytest.mark.parametrize("owner_many", [False, True], ids=["single", "many"])
def test_many_back_mutations(models, owner_many):
    Target, make_owner, check = models(owner_many=owner_many, back_many=True)
    storage = Storage()
    target = Target({"id": 1}, storage)
    first = make_owner(storage)
    second = make_owner(storage)
    third = make_owner(storage)

    owners = target.owners
    owners.append(first)
    check(first, target)
    assert owners == target.owners == [first]

    owners.extend([second])
    check(second, target)
    owners.remove(first)
    check(first)
    assert owners == target.owners == [second]

    target.owners = [first, second, third]
    assert target.owners == [first, second, third]
    check(first, target)
    check(second, target)
    check(third, target)

    target.owners = [third, first]
    assert target.owners == [third, first]
    check(first, target)
    check(second)
    check(third, target)

    target.owners.clear()
    assert target.owners == []
    check(first)
    check(third)


@pytest.mark.parametrize("owner_many", [False, True], ids=["single", "many"])
def test_reverse_lists_acquired_before_pairing_use_the_pair(models, owner_many):
    Target, make_owner, check = models(owner_many=owner_many, back_many=True)
    storage = Storage()
    target = Target({"id": 1}, storage)
    early_list = target.owners

    target.owners.append(make_owner(storage))

    (owner,) = target.owners
    check(owner, target)

    early_list.remove(owner)

    assert early_list == target.owners == []
    check(owner)


@pytest.mark.parametrize("owner_many", [False, True], ids=["single", "many"])
@pytest.mark.parametrize("operation", ["extend", "iadd", "slice", "assign"])
def test_reverse_write_can_resolve_pair_while_consuming_owners(
    models, owner_many, operation
):
    Target, make_owner, check = models(owner_many=owner_many, back_many=True)
    storage = Storage()
    target = Target({"id": 1}, storage)
    owners = target.owners
    created = []

    def new_owners():
        for _ in range(2):
            owner = make_owner(storage)
            created.append(owner)
            yield owner

    if operation == "extend":
        owners.extend(new_owners())
    elif operation == "iadd":
        owners += new_owners()
    elif operation == "slice":
        owners[:] = new_owners()
    else:
        target.owners = new_owners()
        owners = target.owners

    assert owners == target.owners == created
    for owner in created:
        check(owner, target)
    assert (
        storage.get_related_entities(target, type(created[0]), RelationType.RELATED)
        == []
    )


@pytest.mark.parametrize("owner_many", [False, True], ids=["single", "many"])
def test_paired_assignment_requires_the_effective_reverse_field(models, owner_many):
    Target, make_owner, check = models(owner_many=owner_many, back_many=False)
    storage = Storage()
    owner = make_owner(storage, 1)

    class InheritedTarget(Target):
        pass

    class OverriddenTarget(Target):
        owners = Relationship(type(owner))

    inherited = InheritedTarget({"id": 2}, storage)
    overridden = OverriddenTarget({"id": 3}, storage)
    owner.targets = [inherited] if owner_many else inherited
    assert inherited.owners is owner

    with pytest.raises(ValueError, match=r"Owner\.targets.*OverriddenTarget\.owners"):
        owner.targets = [overridden] if owner_many else overridden

    check(owner, inherited)
    assert inherited.owners is owner
    assert overridden.owners is None


@pytest.mark.parametrize("target_first", [True, False], ids=["stored", "pending"])
def test_paired_key_cannot_resolve_to_an_overridden_reverse_field(target_first):
    class Target(Entity):
        id: int = Field(pk=True)
        owner: "Owner | None" = Relationship()

    class Owner(Entity):
        target: Target | None = KeyNested(Target.id, back_populates="owner")

    class OverriddenTarget(Target):
        owner = Relationship(Owner)

    storage = Storage()
    data = {"target": 1}
    error = r"Owner\.target.*OverriddenTarget\.owner"
    if target_first:
        target = OverriddenTarget({"id": 1}, storage)
        with pytest.raises(ValueError, match=error):
            Owner(data, storage)
    else:
        owner = Owner(data, storage)
        target = OverriddenTarget({"id": 1}, storage)
        with pytest.raises(ValueError, match=error):
            owner.target

        replacement = Target({"id": 2}, storage)
        owner.target = replacement
        assert replacement.owner is owner
        assert owner.dict() == {"target": 2}

    assert target.owner is None


def test_many_back_assignment_validates_before_writing(models):
    Target, make_owner, check = models(owner_many=False, back_many=True)
    storage = Storage()
    target = Target({"id": 1}, storage)
    existing = make_owner(storage)
    added = make_owner(storage)
    foreign = make_owner(Storage())
    target.owners = [existing]

    with pytest.raises(ValueError, match="same storage"):
        target.owners = [added, foreign]

    assert target.owners == [existing]
    check(existing, target)
    check(added)
    check(foreign)


def test_separate_pairs_and_manual_relationship():
    class Address(Entity):
        billed_to: "Order | None" = Relationship()
        shipped_to: "Order | None" = Relationship()
        manual: "Order | None" = Relationship()

    class Order(Entity):
        billing: Address | None = Nested(back_populates="billed_to", default=None)
        shipping: Address | None = Nested(back_populates="shipped_to", default=None)

    storage = Storage()
    order = Order({"billing": {}, "shipping": {}}, storage)
    billing, shipping = order.billing, order.shipping
    assert billing.billed_to is shipping.shipped_to is order
    assert billing.shipped_to is shipping.billed_to is None

    order.shipping = billing
    billing.manual = order
    billing.billed_to = None

    assert order.billing is None
    assert order.shipping is billing
    assert billing.shipped_to is billing.manual is order
    assert shipping.shipped_to is None


def test_unpaired_relationship_assigns_owners_as_iterated():
    class Owner(Entity):
        pass

    class Target(Entity):
        owners: list[Owner] = Relationship()

    storage = Storage()
    target = Target({}, storage)
    old, first, second = (Owner({}, storage) for _ in range(3))
    target.owners = [old]

    def owners():
        assert target.owners == []
        yield first
        assert target.owners == [first]
        yield second

    target.owners = owners()
    assert target.owners == [first, second]


def test_move_a_node_through_either_side():
    class Node(Entity):
        children: list["Node"] = Nested(back_populates="parent", default=list)
        parent: "Node | None" = Relationship()

    storage = Storage()
    root = Node({"children": [{}]}, storage)
    other = Node({}, storage)
    child = root.children[0]

    child.parent = other
    assert root.children == []
    assert other.children == [child]
    assert child.parent is other

    root.children.append(child)
    assert root.children == [child]
    assert other.children == []
    assert child.parent is root

    other.children = [child]
    assert root.children == []
    assert other.children == [child]
    assert child.parent is other


@pytest.mark.parametrize("kind", [Nested, KeyNested])
@pytest.mark.parametrize(
    ("name", "message"),
    [("missing", "does not exist"), ("id", "is not a Relationship")],
)
def test_pair_resolution_errors(kind, name, message):
    class Target(Entity):
        id: int = Field(pk=True)

    field = kind(Target.id if kind is KeyNested else "Target", back_populates=name)

    class Owner(Entity):
        target = field

    with pytest.raises(ValueError, match=rf"Owner\.target.*Target\.{name}.*{message}"):
        Owner({"target": None}, Storage())


def test_pair_resolution_rejects_reuse_even_without_loading():
    class Target(Entity):
        owner: "Owner | None" = Relationship()

    class Owner(Entity):
        first: Target | None = Nested(back_populates="owner", default=None)
        second: Target | None = Nested(back_populates="owner", mode=AccessMode.GET)

    with pytest.raises(
        ValueError, match=r"Owner\.second.*Target\.owner.*already paired.*Owner\.first"
    ):
        Owner({}, Storage())


def test_nested_pair_resolves_owning_forward_reference():
    class Owner(Entity):
        target: "Target" = Nested(back_populates="owner")

    class Target(Entity):
        owner: Owner | None = Relationship()

    owner = Owner({"target": {}}, Storage())
    assert owner.target.owner is owner


@pytest.mark.parametrize("kind", [Nested, KeyNested])
@pytest.mark.parametrize("label", [True, RelationType.PARENT, "custom"])
def test_back_relation_is_deprecated_and_keeps_implicit_writes(kind, label):
    class Target(Entity):
        id: int = Field(pk=True)
        owner: "Owner | None" = Relationship(
            relation_type=RelationType.RELATED if label is True else label,
        )

    with pytest.warns(DeprecationWarning, match="back_populates") as warnings:
        field = kind(Target.id if kind is KeyNested else Target, back_relation=label)
    assert warnings[0].filename == __file__

    class Owner(Entity):
        target = field

    storage = Storage()
    if kind is KeyNested:
        target = Target({"id": 1}, storage)
        old = Owner({"target": 1}, storage)
    else:
        old = Owner({"target": {"id": 1}}, storage)
        target = old.target
    new = Owner({"target": None}, storage)
    assert target.owner is old

    target.owner = new

    assert old.target is target
    assert new.target is None
    assert target.owner is new


def test_paired_key_back_write_preserves_pending_keys_and_uses_key_manager():
    class Tag(Entity):
        id: int = Field(pk=True)
        posts: list["Post"] = Relationship()

    class TagKey(KeyManager):
        def get(self, data):
            return data["id"]

        def prepare_to_set(self, entity):
            return {"id": entity.id}

    class Post(Entity):
        tags: list[Tag] = KeyNested(
            Tag.id, origin="tag_keys", key_manager=TagKey(), back_populates="posts"
        )

    storage = Storage()
    post = Post({"tag_keys": [{"id": 9}]}, storage)
    tag = Tag({"id": 1}, storage)
    tag.posts.append(post)
    assert post.dict() == {"tag_keys": [{"id": 9}, {"id": 1}]}
    tag.posts.remove(post)
    assert post.dict() == {"tag_keys": [{"id": 9}]}

    pending = Tag({"id": 9}, storage)
    assert post.tags == [pending]
    assert pending.posts == [post]

    post.tags.append(tag)
    assert tag.posts == [post]
    post.tags.remove(pending)
    assert post.dict() == {"tag_keys": [{"id": 1}]}
    assert pending.posts == []


def test_paired_key_keeps_the_annotated_target_type():
    class Target(Entity):
        id: int = Field(pk=True)
        owner: "Owner | None" = Relationship()

    class Owner(Entity):
        target: Target | None = KeyNested(Target.id, back_populates="owner")

    class SpecializedTarget(Target):
        pass

    storage = Storage()
    target = Target({"id": 1}, storage)
    specialized = SpecializedTarget({"id": 2}, storage)
    owner = Owner({"target": 2}, storage)

    target.owner = owner
    assert owner.target is target
    assert owner.dict() == {"target": 1}
    assert target.owner is owner
    assert specialized.owner is None


@pytest.mark.parametrize("forward", [False, True], ids=["evaluated", "forward"])
def test_paired_key_resolves_target_with_inherited_primary_key(forward):
    class Base(Entity):
        id: int = Field(pk=True)

    class Target(Base):
        owner: "Owner | None" = Relationship()

    annotation = "Target | None" if forward else Target | None

    class Owner(Entity):
        target: annotation = KeyNested(Target.id, back_populates="owner")

    class Sibling(Base):
        pass

    storage = Storage()
    old_owner = Owner({"target": 1}, storage)
    new_owner = Owner({"target": None}, storage)
    target = Target({"id": 1}, storage)
    sibling = Sibling({"id": 2}, storage)

    assert Owner.target.entity_type is Target
    assert old_owner.target is target
    assert target.owner is old_owner

    target.owner = new_owner

    assert target.owner is new_owner
    assert old_owner.target is None
    assert old_owner.dict() == {"target": None}
    assert new_owner.target is target
    assert new_owner.dict() == {"target": 1}

    with pytest.raises(ValueError, match="Expected Target"):
        new_owner.target = sibling
    with pytest.raises(ValueError, match="Expected Target"):
        Owner({"target": 2}, storage)
    assert new_owner.target is target


def test_paired_key_list_edits_keep_unresolved_keys():
    class Tag(Entity):
        id: int = Field(pk=True)
        posts: list["Post"] = Relationship()

    class Post(Entity):
        tags: list[Tag] = KeyNested(Tag.id, back_populates="posts", required=False)

    storage = Storage()
    tag = Tag({"id": 1}, storage)
    other = Tag({"id": 2}, storage)
    post = Post({"tags": [1, 9]}, storage)

    post.tags += [other]
    assert post.tags == [tag, other]
    assert post.dict() == {"tags": [1, 9, 2]}
    assert other.posts == [post]

    post.tags.remove(tag)
    assert post.dict() == {"tags": [9, 2]}
    assert tag.posts == []

    pending = Tag({"id": 9}, storage)
    assert pending.posts == [post]
    assert post.tags == [pending, other]
