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


class KeyGetter:
    def __init__(self, key):
        self.key = key

    def get(self, data: dict):
        return data.get(self.key, None)


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

    def __get__(self, instance: 'Entity', owner):
        if instance:
            return instance._data.get(self.origin)
        else:
            return self

    def __set__(self, instance: 'Entity', value):
        if instance:
            if self.mode & AccessMode.SET:
                instance._data[self.origin] = value
            else:
                raise ValueError(f'Field \'{self.name}\' is read only')

    def __set_name__(self, owner, name):
        self.name = name
        self.owner = owner

        if self.origin is None:
            self.origin = name

        if self.destination is None:
            self.destination = self.origin

    def load(self, data: dict, instance: 'Entity') -> t.Any:
        data = data.get(self.origin, ...)

        if data is ...:
            if self.default is not ...:
                return self.default()
            else:
                raise ValueError(
                    f'No value for field \'{self.name}\' of entity: {type(instance)}',
                )

        return data

    def __repr__(self):
        return f'<Field[{self.owner.__name__}.{self.name}]>'


class Nested(Field):
    def __init__(
        self,
        entity_type: t.Union[str, t.Type['Entity']],
        many: bool = False,
        back_relation: t.Optional[RelationType] = None,
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

        self._entity_type = entity_type
        self.many = many
        self.back_relation = back_relation

    @property
    def entity_type(self) -> t.Type['Entity']:
        if isinstance(self._entity_type, str):
            self._entity_type = registry.get(self._entity_type)

        return self._entity_type

    def _load_one(self, data: t.Any, storage: 'Storage', parent: 'Entity'):
        entity = self.entity_type(data=data, storage=storage)

        if self.back_relation:
            storage.make_relation(
                from_=entity,
                to_=parent,
                relation_type=self.back_relation,
            )

        return entity

    def load(self, data, instance: 'Entity') -> t.NoReturn:
        data = super().load(data, instance)
        storage = instance.storage

        if data is not ... and data is not None:
            if self.many:
                data = [
                    self._load_one(item, storage, instance) for item in data
                ]
            else:
                data = self._load_one(data, storage, instance)

        return data

    def __set__(
        self,
        instance: 'Entity',
        value: t.Union[t.List['Entity'], 'Entity'],
    ):
        if not instance:
            return super().__set__(instance, value)

        if self.back_relation:
            old_value = getattr(instance, self.origin)

            if old_value:
                if self.many:
                    for related_entity in old_value:
                        instance.storage.remove_relation(
                            from_=related_entity,
                            to_=instance,
                            relation_type=self.back_relation,
                        )
                else:
                    instance.storage.remove_relation(
                        from_=old_value,
                        to_=instance,
                        relation_type=self.back_relation,
                    )

            if value:
                if self.many:
                    for entity in value:
                        instance.storage.make_relation(
                            from_=entity,
                            to_=instance,
                            relation_type=self.back_relation,
                        )
                else:
                    instance.storage.make_relation(
                        from_=value,
                        to_=instance,
                        relation_type=self.back_relation,
                    )

        super().__set__(instance, value)


class Relationship(Field):
    def __init__(
        self,
        entity_type: t.Union[str, t.Type['Entity']],
        relation_type: RelationType,
        many: bool = False,
    ):
        super().__init__(mode=AccessMode.GET)

        self._entity_type = entity_type
        self.relation_type = relation_type
        self.many = many

    @property
    def entity_type(self) -> t.Type['Entity']:
        if isinstance(self._entity_type, str):
            self._entity_type = registry.get(self._entity_type)

        return self._entity_type

    def __get__(self, instance: 'Entity', owner):
        if not instance:
            return super().__get__(instance, owner)

        if self.many:
            return instance.storage.get_related_entities(
                instance,
                self.entity_type,
                self.relation_type,
            )
        else:
            return instance.storage.get_one_related_entity(
                instance,
                self.entity_type,
                self.relation_type,
            )


class NestedKey(Field):
    def __init__(
        self,
        related_entity_field: t.Union['Field', t.Any],
        key: t.Union[KeyGetter, str],
        back_relation_type: t.Optional[RelationType] = None,
        many: bool = False,
        mode: AccessMode = AccessMode.GET_LOAD,
        default: t.Union[t.Any, t.Callable[[], t.Any]] = ...,
    ):
        if not related_entity_field.pk:
            raise ValueError(
                f'\'{related_entity_field}\' is not primary key field',
            )

        getter = KeyGetter(key) if not isinstance(key, KeyGetter) else key

        super().__init__(mode=mode, origin=getter.key, default=default)

        self.related_entity_field = related_entity_field
        self.getter = getter
        self.many = many
        self.back_relation_type = back_relation_type

    def _load_one(self, data: t.Any, storage: 'Storage', parent: 'Entity'):
        if self.back_relation_type:
            storage.make_key_relation(
                field_from=self.related_entity_field,
                key_from=data,
                relation_type=self.back_relation_type,
                to=parent,
            )

    def load(self, data: dict, instance: 'Entity') -> t.Any:
        storage = instance.storage
        data = super().load(data, instance)

        if data is not ... and data is not None:
            if self.many:
                for item in data:
                    self._load_one(item, storage, instance)
            else:
                self._load_one(data, storage, instance)

        return data

    def __get__(self, instance: 'Entity', owner):
        if not instance:
            return super().__get__(instance, owner)

        data = self.getter.get(instance._data)

        if data is not None:
            if self.many:
                result = []
                for item in data:
                    entity = instance.storage.get(
                        self.related_entity_field,
                        item,
                    )

                    if not entity:
                        raise ValueError(
                            f'Can\'t find {self.related_entity_field}={item} '
                            f'in storage',
                        )

                    result.append(entity)

                return result
            else:
                return instance.storage.get(self.related_entity_field, data)
