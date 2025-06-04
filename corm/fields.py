import typing as t

from corm import registry
from corm.constants import RelationType, AccessMode

if t.TYPE_CHECKING:
    from corm.entity import Entity
    from corm.storage import Storage


def proxy_factory(value: t.Any) -> t.Callable[[], t.Any]:
    def proxy():
        return value

    return proxy


class KeyManager:
    def get(self, data):
        raise NotImplementedError

    def prepare_to_set(self, entity: "Entity") -> t.Any:
        raise NotImplementedError


class DefaultKeyManager:
    def __init__(self, field: "Field"):
        self.field = field

    def get(self, data):
        return data

    def prepare_to_set(self, entity: "Entity") -> t.Any:
        if entity:
            return getattr(entity, self.field.name)


class RelationshipList(list):
    def __init__(
        self,
        entity: "Entity",
        items: t.Iterable["Entity"],
        relation_type: t.Any = None,
    ):
        super().__init__(items)

        self.entity = entity
        self.relation_type = relation_type

    def make_relation(self, entity):
        return self.entity.storage.make_relation(
            from_=self.entity,
            to_=entity,
            relation_type=self.relation_type,
        )

    def remove_relation(self, entity):
        self.entity.storage.remove_relation(
            from_=self.entity,
            to_=entity,
            relation_type=self.relation_type,
        )

    def append(self, entity: "Entity") -> None:
        super().append(entity)

        if self.relation_type:
            self.make_relation(entity)

    def extend(self, entities: t.List["Entity"]) -> None:
        for entity in entities:
            super().append(entity)

            if self.relation_type:
                self.make_relation(entity)

    def remove(self, entity: "Entity") -> None:
        super().remove(entity)

        if self.relation_type:
            self.remove_relation(entity)

    def insert(self, index: int, entity: "Entity") -> None:
        raise NotImplementedError

    def pop(self, index: int = ...) -> "Entity":
        raise NotImplementedError

    def clear(self) -> None:
        if self.relation_type:
            for entity in self:
                self.remove_relation(entity)

        super().clear()


class NestedList(RelationshipList):
    def __init__(
        self,
        entity: "Entity",
        items: t.Iterable["Entity"],
        relation_type: t.Any = None,
    ):
        super().__init__(
            entity=entity,
            items=items,
            relation_type=relation_type,
        )

        if relation_type:
            for item in self:
                entity.storage.make_relation(
                    from_=item,
                    to_=entity,
                    relation_type=relation_type,
                )

    def make_relation(self, entity):
        return self.entity.storage.make_relation(
            from_=entity,
            to_=self.entity,
            relation_type=self.relation_type,
        )

    def remove_relation(self, entity):
        self.entity.storage.remove_relation(
            from_=entity,
            to_=self.entity,
            relation_type=self.relation_type,
        )


class KeyRelationshipList(list):
    """TODO"""


class Field:
    name: str
    pk: bool
    mode: int
    default: t.Callable[[], t.Any]
    origin: t.Optional[str]
    destination: t.Optional[str]

    def __init__(
        self,
        pk: bool = False,
        mode: AccessMode = AccessMode.ALL,
        default: t.Union[t.Any, t.Callable[[], t.Any]] = ...,
        origin: t.Optional[str] = None,
        destination: t.Optional[str] = None,
    ):
        self.pk = pk
        self.mode = mode
        self.origin = origin
        self.destination = destination

        if default is not ... and not callable(default):
            default = proxy_factory(default)

        self.default = default

    def __get__(self, instance: "Entity", owner) -> t.Any:
        if instance:
            return instance._data.get(self.origin)
        else:
            return self

    def __set__(self, instance: "Entity", value):
        if instance:
            if self.mode & AccessMode.SET:
                instance._data[self.origin] = value
            else:
                raise ValueError(f"Field '{self.name}' is read only")
        else:
            raise ValueError("Not able to change field on class")

    def __set_name__(self, owner, name):
        self.name = name
        self.owner = owner

        if self.origin is None:
            self.origin = name

        if self.destination is None:
            self.destination = self.origin

    def load(self, data: dict, instance: "Entity") -> t.Any:
        data = data.get(self.origin, ...)

        if data is ...:
            if self.default is not ...:
                return self.default()
            else:
                raise ValueError(
                    f"No value for field '{self.name}' of entity: {type(instance)}",
                )

        return data

    def __repr__(self):
        return f"<Field[{self.owner.__name__}.{self.name}]>"


class Nested(Field):
    def __init__(
        self,
        entity_type: t.Union[str, t.Type["Entity"]],
        many: bool = False,
        back_relation: t.Any = False,
        mode: AccessMode = AccessMode.ALL,
        default: t.Union[t.Any, t.Callable[[], t.Any]] = ...,
        origin: str = None,
        destination: str = None,
    ):
        super().__init__(
            mode=mode,
            default=default,
            origin=origin,
            destination=destination,
        )

        if isinstance(back_relation, bool) and back_relation:
            back_relation = RelationType.RELATED

        self._entity_type = entity_type
        self.many = many
        self.back_relation = back_relation

    @property
    def entity_type(self) -> t.Type["Entity"]:
        if isinstance(self._entity_type, str):
            self._entity_type = registry.get(self._entity_type)

        return self._entity_type

    def _load_one(self, data: t.Any, storage: "Storage", parent: "Entity"):
        entity = self.entity_type(data=data, storage=storage)

        return entity

    def load(self, data, instance: "Entity") -> t.NoReturn:
        data = super().load(data, instance)
        storage = instance.storage

        if self.many:
            items = (self.entity_type(data=item, storage=storage) for item in data)
            data = NestedList(
                entity=instance,
                items=items,
                relation_type=self.back_relation,
            )

        else:
            data = self.entity_type(data=data, storage=storage)

            if self.back_relation:
                storage.make_relation(
                    from_=data,
                    to_=instance,
                    relation_type=self.back_relation,
                )

        return data

    def __set__(
        self,
        instance: "Entity",
        value: t.Union[t.List["Entity"], "Entity"],
    ):
        if not instance:
            return super().__set__(instance, value)

        old_value = getattr(instance, self.origin)

        if self.many:
            if not isinstance(value, list):
                raise ValueError(
                    f"Only list accepted for nested field with many set to True, got: {value}",
                )

            old_value.clear()

            value = NestedList(
                entity=instance,
                items=value,
                relation_type=self.back_relation,
            )
        else:
            if self.back_relation:
                instance.storage.remove_relation(
                    from_=old_value,
                    to_=instance,
                    relation_type=self.back_relation,
                )

            if value:
                instance.storage.make_relation(
                    from_=value,
                    to_=instance,
                    relation_type=self.back_relation,
                )

        super().__set__(instance, value)


class Relationship(Field):
    def __init__(
        self,
        entity_type: t.Union[str, t.Type["Entity"]],
        relation_type: t.Any = RelationType.RELATED,
        many: bool = False,
    ):
        super().__init__(mode=AccessMode.GET)

        self._entity_type = entity_type
        self.relation_type = relation_type
        self.many = many

    @property
    def entity_type(self) -> t.Type["Entity"]:
        if isinstance(self._entity_type, str):
            self._entity_type = registry.get(self._entity_type)

        return self._entity_type

    def __get__(self, instance: "Entity", owner):
        if not instance:
            return super().__get__(instance, owner)

        if self.many:
            entities = instance.storage.get_related_entities(
                instance,
                self.entity_type,
                self.relation_type,
            )

            return RelationshipList(
                entity=instance,
                items=entities,
                relation_type=self.relation_type,
            )
        else:
            return instance.storage.get_one_related_entity(
                instance,
                self.entity_type,
                self.relation_type,
            )

    def __set__(self, instance, value):
        if not instance:
            return super().__set__(instance, value)

        instance.storage.remove_relations(
            instance,
            self.entity_type,
            self.relation_type,
        )

        if value:
            if self.many:
                for entity in value:
                    instance.storage.make_relation(
                        from_=instance,
                        to_=entity,
                        relation_type=self.relation_type,
                    )
            else:
                instance.storage.make_relation(
                    from_=instance,
                    to_=value,
                    relation_type=self.relation_type,
                )


class KeyNested(Field):
    def __init__(
        self,
        related_entity_field: t.Union["Field", t.Any],
        back_relation: t.Any = False,
        many: bool = False,
        mode: AccessMode = AccessMode.GET_SET_LOAD,
        default: t.Union[t.Any, t.Callable[[], t.Any]] = ...,
        origin: t.Optional[str] = None,
        destination: t.Optional[str] = None,
        key_manager: t.Optional[KeyManager] = None,
        required: bool = True,
    ):
        if not related_entity_field.pk:
            raise ValueError(
                f"'{related_entity_field}' is not primary key field",
            )

        super().__init__(
            mode=mode,
            origin=origin,
            destination=destination,
            default=default,
        )

        if isinstance(back_relation, bool) and back_relation:
            back_relation = RelationType.RELATED

        self.related_entity_field = related_entity_field
        self.key_manager = key_manager or DefaultKeyManager(
            field=related_entity_field,
        )
        self.many = many
        self.back_relation = back_relation
        self.required = required

    def _load_one(self, data: t.Any, storage: "Storage", parent: "Entity"):
        if self.back_relation:
            storage.make_key_relation(
                field_from=self.related_entity_field,
                key_from=data,
                relation_type=self.back_relation,
                to=parent,
            )

    def load(self, data: dict, instance: "Entity") -> t.Any:
        storage = instance.storage
        data = super().load(data, instance)

        if data is None:
            return

        if self.many:
            for item in data:
                key = self.key_manager.get(item)
                self._load_one(key, storage, instance)
        else:
            key = self.key_manager.get(data)
            self._load_one(key, storage, instance)

        return data

    def __get__(self, instance: "Entity", owner):
        data = super().__get__(instance, owner)

        if not instance or data is None:
            return data

        if self.many:
            result = []

            for item in data:
                key = self.key_manager.get(item)

                entity = instance.storage.get(
                    field=self.related_entity_field,
                    entity_key=key,
                )

                if not entity:
                    if self.required:
                        raise ValueError(
                            f"Can't find {self.related_entity_field}={key} "
                            f"in storage",
                        )
                    else:
                        continue

                result.append(entity)

            return result
        else:
            key = self.key_manager.get(data)
            entity = instance.storage.get(self.related_entity_field, key)

            if not entity and self.required:
                raise ValueError(
                    f"Can't find {self.related_entity_field}={key} " f"in storage",
                )

            return entity

    def __set__(
        self,
        instance: "Entity",
        value: t.Union["Entity", t.List["Entity"]],
    ):
        if not instance:
            return super().__set__(instance, value)

        if self.many:
            if self.back_relation:
                for old_related_entity in getattr(instance, self.name):
                    instance.storage.remove_relation(
                        from_=old_related_entity,
                        to_=instance,
                        relation_type=self.back_relation,
                    )

            new_data = []

            for related_entity in value:
                new_data.append(self.key_manager.prepare_to_set(related_entity))

                if self.back_relation:
                    instance.storage.make_relation(
                        from_=related_entity,
                        to_=instance,
                        relation_type=self.back_relation,
                    )

        else:
            if self.back_relation:
                old_related_entity = getattr(instance, self.name)

                if old_related_entity:
                    instance.storage.remove_relation(
                        from_=old_related_entity,
                        to_=instance,
                        relation_type=self.back_relation,
                    )

            new_data = self.key_manager.prepare_to_set(value)

            if self.back_relation:
                instance.storage.make_relation(
                    from_=value,
                    to_=instance,
                    relation_type=self.back_relation,
                )

        super().__set__(instance, new_data)
