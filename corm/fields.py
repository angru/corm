import typing as t

from corm import constants, registry

if t.TYPE_CHECKING:
    from corm.model import Model
    from corm.storage import Storage

#
# class Path:
#     def __init__(self, *fields: t.List['Field']):
#         self._fields: t.List['Field'] = fields
#
#     def match(self, field: 'Field') -> bool:
#         pass
#
#     def get(self, data: dict):
#         for field in self._fields:
#             if field.name in data:
#                 if field


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
            self, pk: bool = False, mode: int = constants.AccessMode.ALL,
            default: t.Union[t.Any, t.Callable[[], t.Any]] = ...,
    ):
        self.pk = pk
        self.mode = mode

        if default is not ... and not callable(default):
            default = proxy_factory(default)

        self.default = default

    def __get__(self, instance: 'Model', owner):
        if instance:
            return instance._data.get(self.name)
        else:
            return self

    def __set__(self, instance: 'Model', value):
        instance._data[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name

    def load(self, data, instance: 'Model') -> t.Any:
        if data is ... and self.default is not ...:
            return self.default()

        return data


class Nested(Field):
    def __init__(
            self,
            entity_type: t.Union[str, t.Type['Model']],
            many: bool = False,
            relation_type: constants.RelationType = constants.RelationType.RELATED,
            back_relation_type: t.Optional[constants.RelationType] = None,
            mode: int = constants.AccessMode.ALL,
            default: t.Union[t.Any, t.Callable[[], t.Any]] = ...,
    ):
        super().__init__(mode=mode, default=default)

        self._entity_type = entity_type
        self.many = many
        self.relation_type = relation_type
        self.back_relation_type = back_relation_type

    @property
    def entity_type(self) -> t.Type['Model']:
        if isinstance(self._entity_type, str):
            self._entity_type = registry.get(self._entity_type)

        return self._entity_type

    def _load_one(self, data: t.Any, storage: 'Storage', parent: 'Model'):
        entity = self.entity_type(data=data, storage=storage)

        if self.relation_type:
            storage.make_relation(from_=parent, relation_type=self.relation_type, to_=entity)

        if self.back_relation_type:
            storage.make_relation(from_=entity, relation_type=self.back_relation_type, to_=parent)

    def load(self, data, instance: 'Model') -> t.NoReturn:
        storage = instance._storage
        data = super().load(data, instance)

        if data is not ...:
            if self.many:
                for item in data:
                    self._load_one(item, storage, instance)
            else:
                self._load_one(data, storage, instance)

        return data

    def __get__(self, instance: 'Model', owner):
        if instance:
            if self.many:
                return instance._storage.get_related_entities(instance, self.entity_type, self.relation_type)
            else:
                return instance._storage.get_one_related_entity(instance, self.entity_type, self.relation_type)
        else:
            return super().__get__(instance, owner)

    def __set__(self, instance, value):
        raise NotImplementedError


class Relationship(Nested):
    def __init__(
            self,
            entity_type: t.Union[str, t.Type['Model']],
            relation_type: constants.RelationType = constants.RelationType.RELATED,
            many: bool = False,
            mode: int = constants.AccessMode.GET,
            default: t.Union[t.Any, t.Callable[[], t.Any]] = ...,
    ):
        super().__init__(entity_type=entity_type, relation_type=relation_type, many=many, mode=mode, default=default)


class KeyRelationship(Field):
    def __init__(
            self,
            related_entity_field,
            key: str,
            many: bool = False,
            mode: int = constants.AccessMode.GET,
    ):
        super().__init__(mode=mode)

        if not related_entity_field.pk:
            raise ValueError(f'{related_entity_field} is not primary key field')

        self.related_entity_field = related_entity_field
        self.key = key
        self.many = many

    def __get__(self, instance: 'Model', owner):
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

    @property
    def entity_type(self) -> t.Type['Model']:
        if isinstance(self.related_entity_field, str):
            self.related_entity_field = registry.get(self.related_entity_field)

        return self.related_entity_field