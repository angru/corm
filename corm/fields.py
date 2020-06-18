import typing as t

from corm import constants, registry

if t.TYPE_CHECKING:
    from corm.entity import Entity
    from corm.storage import Storage


def proxy_factory(value: t.Any) -> t.Callable[[], t.Any]:
    def proxy():
        return value

    return proxy


class Field:
    name: str
    pk: bool
    mode: int
    default: t.Callable[[], t.Any]

    def __init__(
            self, pk: bool = False, mode: constants.AccessMode = constants.AccessMode.ALL,
            default: t.Union[t.Any, t.Callable[[], t.Any]] = ...,
    ):
        self.pk = pk
        self.mode = mode

        if default is not ... and not callable(default):
            default = proxy_factory(default)

        self.default = default

    def __get__(self, instance: 'Entity', owner):
        if instance:
            return instance._data.get(self.name)
        else:
            return self

    def __set__(self, instance: 'Entity', value):
        instance._data[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name
        self.owner = owner

    def load(self, data: dict, instance: 'Entity') -> t.Any:
        data = data.get(self.name, ...)

        if data is ... and self.default is not ...:
            return self.default()

        return data

    def __repr__(self):
        return f'<Field[{self.owner.__name__}.{self.name}]>'


class Nested(Field):
    def __init__(
            self,
            entity_type: t.Union[str, t.Type['Entity']],
            many: bool = False,
            relation_type: constants.RelationType = constants.RelationType.PARENT,
            back_relation_type: t.Optional[constants.RelationType] = None,
            mode: constants.AccessMode = constants.AccessMode.ALL,
            default: t.Union[t.Any, t.Callable[[], t.Any]] = ...,
    ):
        super().__init__(mode=mode, default=default)

        self._entity_type = entity_type
        self.many = many
        self.relation_type = relation_type
        self.back_relation_type = back_relation_type

    @property
    def entity_type(self) -> t.Type['Entity']:
        if isinstance(self._entity_type, str):
            self._entity_type = registry.get(self._entity_type)

        return self._entity_type

    def _load_one(self, data: t.Any, storage: 'Storage', parent: 'Entity'):
        entity = self.entity_type(data=data, storage=storage)

        if self.relation_type:
            storage.make_relation(from_=parent, to_=entity, relation_type=self.relation_type)

        if self.back_relation_type:
            storage.make_relation(from_=entity, to_=parent, relation_type=self.back_relation_type)

    def load(self, data, instance: 'Entity') -> t.NoReturn:
        data = super().load(data, instance)
        storage = instance._storage

        if data is not ...:
            if self.many:
                for item in data:
                    self._load_one(item, storage, instance)
            else:
                self._load_one(data, storage, instance)

        return data

    def __get__(self, instance: 'Entity', owner):
        if not instance:
            return super().__get__(instance, owner)

        if self.many:
            return instance._storage.get_related_entities(instance, self.entity_type, self.relation_type)
        else:
            return instance._storage.get_one_related_entity(instance, self.entity_type, self.relation_type)

    def __set__(self, instance, value):
        raise NotImplementedError


class Relationship(Nested):
    def __init__(
            self,
            entity_type: t.Union[str, t.Type['Entity']],
            relation_type: constants.RelationType,
            many: bool = False,
            mode: constants.AccessMode = constants.AccessMode.GET,
            default: t.Union[t.Any, t.Callable[[], t.Any]] = ...,
    ):
        super().__init__(entity_type=entity_type, relation_type=relation_type, many=many, mode=mode, default=default)


class NestedKey(Field):
    def __init__(
            self,
            related_entity_field: t.Union['Field', t.Any],
            key: str,
            back_relation_type: t.Optional[constants.RelationType] = None,
            many: bool = False,
            mode: constants.AccessMode = constants.AccessMode.GET_LOAD,
    ):
        if not related_entity_field.pk:
            raise ValueError(f'{related_entity_field} is not primary key field')

        super().__init__(mode=mode)

        self.related_entity_field = related_entity_field
        self.key = key
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
        storage = instance._storage
        data = data.get(self.key, ...)

        if data is not ...:
            if self.many:
                for item in data:
                    self._load_one(item, storage, instance)
            else:
                self._load_one(data, storage, instance)

        return data

    def __get__(self, instance: 'Entity', owner):
        if not instance:
            return super().__get__(instance, owner)

        data = instance._data.get(self.key)

        if data is not None:
            if self.many:
                result = []
                for item in data:
                    entity = instance._storage.get(self.related_entity_field, item)

                    if not entity:
                        raise ValueError(f'Can\'t find {self.related_entity_field}={item} in storage')

                    result.append(entity)

                return result
            else:
                return instance._storage.get(self.related_entity_field, data)


class KeyRelationship(Field):
    def __init__(
            self,
            entity_type: t.Union[str, t.Type['Entity']],
            field_name: str, relation_type: constants.RelationType,
            many: bool = False,
            mode: constants.AccessMode = constants.AccessMode.GET,
    ):
        super().__init__(mode=mode)

        self._entity_type = entity_type
        self.field_name = field_name
        self.relation_type = relation_type
        self.many = many

    @property
    def entity_type(self) -> t.Type['Entity']:
        if isinstance(self._entity_type, str):
            self._entity_type = registry.get(self._entity_type)

        return self._entity_type

    def __get__(self, instance: 'Entity', owner: t.Type['Entity']):
        if not instance:
            return super().__get__(instance, owner)

        field = instance.__fields__[self.field_name]
        key = getattr(instance, self.field_name, None)

        if self.many:
            return instance._storage.get_key_relations(
                field_from=field,
                key_from=key,
                relation_type=self.relation_type,
                to=self.entity_type,
            )
        else:
            return instance._storage.get_one_key_related_entity(
                field_from=field,
                key_from=key,
                relation_type=self.relation_type,
                to=self.entity_type,
            )

# class EntityRef:
#     def __init__(self, key: t.Any, field: Field, storage: 'Storage'):
#         self.key = key
#         self.field = field
#         self.storage = storage
#
#     def get(self):
#         return self.storage.get(self.field, self.key)
