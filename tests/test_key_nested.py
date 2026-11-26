import typing as t

import pytest

from corm import (
    Entity,
    Field,
    KeyManager,
    KeyNested,
    Relationship,
    RelationType,
    Storage,
)


def test_nested_key():
    class SomeEntity(Entity):
        id: int = Field(pk=True)
        name: str

    class EntityHolder(Entity):
        entity: SomeEntity = KeyNested(
            related_entity_field=SomeEntity.id,
            origin="entity_id",
        )

    storage = Storage()
    entity = SomeEntity({"id": 123, "name": "entity"}, storage=storage)
    holder = EntityHolder({"entity_id": 123}, storage=storage)

    assert holder.entity == entity
    assert holder.dict() == {"entity_id": 123}

    class ManyEntityHolder(Entity):
        entities: list[SomeEntity] = KeyNested(
            related_entity_field=SomeEntity.id,
            origin="entity_ids",
            many=True,
        )

    storage = Storage()
    entity1 = SomeEntity({"id": 123, "name": "entity1"}, storage=storage)
    entity2 = SomeEntity({"id": 321, "name": "entity2"}, storage=storage)
    holder = ManyEntityHolder({"entity_ids": [123, 321]}, storage=storage)

    assert holder.entities == [entity1, entity2]
    assert holder.dict() == {"entity_ids": [123, 321]}

    storage = Storage()
    SomeEntity({"id": 123, "name": "entity1"}, storage=storage)
    SomeEntity({"id": 321, "name": "entity2"}, storage=storage)
    holder = ManyEntityHolder({"entity_ids": [123, 99999]}, storage=storage)

    with pytest.raises(ValueError):
        holder.entities


def test_make_back_relationship():
    class SomeEntity(Entity):
        id: int = Field(pk=True)
        name: str
        holder: "EntityHolder" = Relationship("EntityHolder")

    class EntityHolder(Entity):
        entities: list[SomeEntity] = KeyNested(
            related_entity_field=SomeEntity.id,
            origin="entity_ids",
            many=True,
            back_relation=True,
        )

    storage = Storage()
    entity = SomeEntity({"id": 123, "name": "entity"}, storage=storage)
    holder = EntityHolder({"entity_ids": [123, 456]}, storage=storage)
    delayed_entity = SomeEntity(
        {
            "id": 456,
            "name": "delayed entity",
        },
        storage=storage,
    )

    assert holder.entities == [entity, delayed_entity]
    assert entity.holder == holder
    assert delayed_entity.holder == holder

    assert holder.dict({"entity_ids": [123, 456]})
    assert entity.dict() == {"id": 123, "name": "entity"}
    assert delayed_entity.dict() == {"id": 456, "name": "delayed entity"}


def test_pending_back_relationships_include_subclasses_in_creation_order():
    class Team(Entity):
        id: int = Field(pk=True)
        members = Relationship(entity_type="Member", many=True)
        managers = Relationship(entity_type="Manager", many=True)

    class Member(Entity):
        team = KeyNested(Team.id, origin="team_id", back_relation=True)

    class Manager(Member):
        pass

    class Director(Manager):
        pass

    class Contractor(Member):
        pass

    storage = Storage()
    director = Director({"team_id": 1}, storage)
    member = Member({"team_id": 1}, storage)
    contractor = Contractor({"team_id": 1}, storage)
    team = Team({"id": 1}, storage)
    manager = Manager({"team_id": 1}, storage)

    assert director.team is team
    assert team.members == [director, member, contractor, manager]
    assert team.managers == [director, manager]


def test_complex_key():
    class SomeEntity(Entity):
        id: int = Field(pk=True)
        name: str

    class EntityKeyManager(KeyManager):
        def get(self, data):
            return data["id"]

        def prepare_to_set(self, entity: SomeEntity) -> t.Any:
            return {"id": entity.id}

    class ManyEntityHolder(Entity):
        entities: list[SomeEntity] = KeyNested(
            related_entity_field=SomeEntity.id,
            origin="entity_ids",
            many=True,
            key_manager=EntityKeyManager(),
        )

    storage = Storage()
    entity1 = SomeEntity({"id": 123, "name": "entity1"}, storage=storage)
    entity2 = SomeEntity({"id": 321, "name": "entity2"}, storage=storage)
    holder = ManyEntityHolder(
        {
            "entity_ids": [
                {
                    "id": 123,
                },
                {
                    "id": 321,
                },
            ],
        },
        storage=storage,
    )

    assert holder.entities == [entity1, entity2]
    assert holder.dict() == {"entity_ids": [{"id": 123}, {"id": 321}]}


def test_change_values():
    class SomeEntity(Entity):
        id: int = Field(pk=True)
        name: str
        holder: "EntityHolder" = Relationship(entity_type="EntityHolder")
        many_holder: "ManyEntityHolder" = Relationship(
            entity_type="ManyEntityHolder",
        )

    class EntityKeyManager(KeyManager):
        def get(self, data):
            return data["id"]

        def prepare_to_set(self, entity: SomeEntity) -> t.Any:
            return {"id": entity.id}

    class EntityHolder(Entity):
        entity: SomeEntity = KeyNested(
            related_entity_field=SomeEntity.id,
            origin="entity_id",
            key_manager=EntityKeyManager(),
            back_relation=True,
        )

    class ManyEntityHolder(Entity):
        entities: list[SomeEntity] = KeyNested(
            related_entity_field=SomeEntity.id,
            origin="entity_ids",
            many=True,
            back_relation=True,
            key_manager=EntityKeyManager(),
        )

    storage = Storage()
    entity1 = SomeEntity({"id": 123, "name": "entity1"}, storage=storage)
    entity2 = SomeEntity({"id": 321, "name": "entity2"}, storage=storage)
    holder = EntityHolder(
        {
            "entity_id": {
                "id": 123,
            },
        },
        storage=storage,
    )

    holder.entity = entity2

    assert entity1.holder is None
    assert entity2.holder is holder
    assert holder.entity is entity2
    assert holder.dict() == {"entity_id": {"id": 321}}

    many_holder = ManyEntityHolder(
        {
            "entity_ids": [
                {
                    "id": 123,
                }
            ],
        },
        storage=storage,
    )

    many_holder.entities = [entity2]

    assert many_holder.entities == [entity2]
    assert entity1.many_holder is None
    assert entity2.many_holder is many_holder
    assert many_holder.dict() == {
        "entity_ids": [
            {
                "id": 321,
            }
        ],
    }


@pytest.mark.parametrize("required", [True, False])
def test_old_key_reference_dangles_after_primary_key_change(required):
    class SomeEntity(Entity):
        id: int = Field(pk=True)
        name: str

    class EntityHolder(Entity):
        entity: SomeEntity = KeyNested(
            related_entity_field=SomeEntity.id,
            required=required,
            origin="entity_id",
        )

    storage = Storage()
    entity = SomeEntity({"id": 123, "name": "entity"}, storage=storage)
    holder = EntityHolder({"entity_id": 123}, storage=storage)
    assert holder.entity is entity

    entity.id = 321

    if required:
        with pytest.raises(ValueError, match=r"Can't find .*123 in storage"):
            holder.entity
    else:
        assert holder.entity is None
    assert holder.dict() == {"entity_id": 123}


def test_primary_key_change_attaches_pending_back_relations():
    class Target(Entity):
        id: int = Field(pk=True)
        holders = Relationship(entity_type="Holder", many=True)

    class Holder(Entity):
        target = KeyNested(Target.id, back_relation=True, required=False)

    class SpecialHolder(Holder):
        pass

    storage = Storage()
    target = Target({"id": 1}, storage)
    existing = Holder({"target": None}, storage)
    target.holders.append(existing)
    pending = SpecialHolder({"target": 5}, storage)
    assert pending.target is None

    target.id = 5

    assert pending.target is target
    assert target.holders == [existing, pending]
    special_holders = storage.get_related_entities(
        target, SpecialHolder, RelationType.RELATED
    )
    assert special_holders == [pending]


def test_unpaired_append_preserves_records_and_pending_references():
    class Target(Entity):
        id: int = Field(pk=True)

    class RecordKey(KeyManager):
        def get(self, data):
            return data["id"]

        def prepare_to_set(self, entity):
            return {"id": entity.id, "meta": {"new": True}}

    class Owner(Entity):
        targets: list[Target] = KeyNested(
            Target.id,
            origin="keys",
            many=True,
            key_manager=RecordKey(),
            required=False,
        )

    storage = Storage()
    first = Target({"id": 1}, storage)
    second = Target({"id": 2}, storage)
    records = [{"id": 1, "meta": {"old": [1]}}, {"id": 9}, {"id": 1}]
    owner = Owner({"keys": records}, storage)
    view = owner.targets
    owner.targets.append(first)
    view.append(second)
    expected = [
        *records,
        {"id": 1, "meta": {"new": True}},
        {"id": 2, "meta": {"new": True}},
    ]
    assert owner.dict() == {"keys": expected}
    pending = Target({"id": 9}, storage)
    assert owner.targets == [first, pending, first, first, second]
    assert view == [first, first, second]


def test_unpaired_append_rejects_invalid_targets_without_writes():
    from corm import AccessMode, ReadOnlyFieldError, RelationError

    class Target(Entity):
        id: int = Field(pk=True)

    class Owner(Entity):
        targets: list[Target] = KeyNested(Target.id, many=True)
        readonly: list[Target] = KeyNested(
            Target.id, many=True, mode=AccessMode.GET_LOAD
        )

    storage = Storage()
    target = Target({"id": 1}, storage)
    foreign = Target({"id": 2}, Storage())
    owner = Owner({"targets": [], "readonly": []}, storage)
    view = owner.targets
    for invalid in (object(), foreign):
        with pytest.raises(RelationError):
            view.append(invalid)
    with pytest.raises(ReadOnlyFieldError):
        owner.readonly.append(target)
    target.id = 3
    # A target whose key manager no longer points to it is also rejected.
    target._data["id"] = 4
    with pytest.raises(RelationError):
        view.append(target)
    assert owner.dict() == {"targets": [], "readonly": []}
    assert view == []


def test_legacy_unpaired_append_updates_reverse_and_rejects_duplicate():
    from corm import RelationError

    class Target(Entity):
        id: int = Field(pk=True)
        owners: list["Owner"] = Relationship()

    class Owner(Entity):
        targets: list[Target] = KeyNested(
            Target.id, many=True, back_relation=True, required=False
        )

    storage = Storage()
    owner = Owner({"targets": [9]}, storage)
    target = Target({"id": 1}, storage)
    view = owner.targets
    view.append(target)
    assert target.owners == [owner]
    with pytest.raises(RelationError):
        view.append(target)
    assert owner.dict() == {"targets": [9, 1]}
    assert view == [target]
    pending = Target({"id": 9}, storage)
    assert pending.owners == [owner]
