import typing as t

from corm import registry, constants
from corm.fields import Field

if t.TYPE_CHECKING:
    from corm.storage import Storage
    from corm.hooks import Hook


class EntityMeta(type):
    def __new__(mcs, name, bases, attrs: t.Dict[str, t.Any]):
        fields = {}
        pk_fields = []

        for base in bases:
            if issubclass(base, Entity) and base != Entity:
                fields.update(base.__fields__)

        annotations = attrs.get('__annotations__') or {}

        if bases:
            for attr_name, attr_value in attrs.items():
                if isinstance(attr_value, Field):
                    fields[attr_name] = attr_value

                    if attr_value.pk:
                        pk_fields.append(attr_value)
                elif not attr_name.startswith('_') and attr_name in annotations:
                    fields[attr_name] = Field()

            for attr_name, type_ in annotations.items():
                if not attr_name.startswith('_') and attr_name not in fields:
                    fields[attr_name] = Field()

        attrs['__fields__'] = fields

        if pk_fields:
            attrs['__pk_fields__'] = pk_fields

        attrs.update(fields)

        klass = super().__new__(mcs, name, bases, attrs)

        registry.add(klass)

        return klass


class Entity(metaclass=EntityMeta):
    _data: t.Dict[str, t.Any]
    _storage: 'Storage'
    __pk_fields__: t.Optional[t.List[Field]] = None
    __fields__: t.Dict[str, Field]

    def __init__(self, data: t.Any, storage: 'Storage'):
        self._data = data
        self._storage = storage

        if self.__pk_fields__:
            storage.add(self)

        for name, field in self.__fields__.items():
            if field.mode & constants.AccessMode.LOAD:
                value = field.load(data, self)

                if value is not ...:
                    data[name] = value

    def dict(self, strip_none=False, hooks: t.Optional[t.List['Hook']] = None):
        data = self._data

        for name, field in self.__fields__.items():
            if field.mode & constants.AccessMode.DUMP:
                value = getattr(self, name)

                if strip_none and value is None:
                    continue

                if isinstance(value, Entity):
                    value = value.dict(strip_none=strip_none)

                data[name] = value

        return data
