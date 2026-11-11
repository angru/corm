import sys
import typing as t

from corm import constants, registry
from corm.fields import Field, Nested

if t.TYPE_CHECKING:
    from corm.storage import Storage

if sys.version_info >= (3, 14):
    import annotationlib

    def _namespace_annotations(attrs):
        annotate = annotationlib.get_annotate_from_class_namespace(attrs)
        if annotate is None:
            return attrs.get("__annotations__") or {}
        return annotationlib.call_annotate_function(
            annotate, annotationlib.Format.FORWARDREF
        )

else:

    def _namespace_annotations(attrs):
        return attrs.get("__annotations__") or {}


class EntityMeta(type):
    def __new__(mcs, name, bases, attrs: dict[str, t.Any]):
        fields = {}
        pk_fields = []

        for base in bases:
            if issubclass(base, Entity) and base != Entity:
                fields.update(base.__fields__)

        annotations = _namespace_annotations(attrs)

        if bases:
            for attr_name, attr_value in attrs.items():
                if isinstance(attr_value, Field):
                    fields[attr_name] = attr_value

                    if attr_value.pk:
                        pk_fields.append(attr_value)
                elif (
                    not attr_name.startswith("_")
                    and not isinstance(
                        attr_value, (property, classmethod, staticmethod)
                    )
                    and not callable(attr_value)
                ):
                    fields[attr_name] = Field(default=attr_value)

            # A class can supply its own annotations mapping.
            for attr_name, _ in annotations.items():  # noqa: PERF102
                if not attr_name.startswith("_") and attr_name not in fields:
                    fields[attr_name] = Field()

        attrs["__fields__"] = fields

        if pk_fields:
            attrs["__pk_fields__"] = pk_fields

        attrs.update(fields)

        klass = super().__new__(mcs, name, bases, attrs)

        if klass.__pk_fields__:
            pk_names = {field.name for field in klass.__pk_fields__}
            klass._field_load_groups = (
                tuple(field for name, field in fields.items() if name in pk_names),
                tuple(field for name, field in fields.items() if name not in pk_names),
            )

        registry.add(klass)

        return klass


class Entity(metaclass=EntityMeta):
    _data: dict[str, t.Any]
    storage: "Storage"
    __pk_fields__: list[Field] | None = None
    __fields__: dict[str, Field]
    _field_load_groups: tuple[tuple[Field, ...], tuple[Field, ...]]

    def __init__(self, data: t.Any, storage: "Storage"):
        self._data = data
        self.storage = storage

        pk_fields = self.__pk_fields__
        if pk_fields:
            # Reject duplicate keys before other fields can add entities or relations.
            key_fields, remaining_fields = self._field_load_groups
            self._load_fields(key_fields, data)
            for field in pk_fields:
                storage._check_primary_key(field, getattr(self, field.name))
        else:
            remaining_fields = self.__fields__.values()

        self._load_fields(remaining_fields, data)
        if pk_fields:
            storage.add(self)

    def _load_fields(self, fields: t.Iterable[Field], data: t.Any):
        for field in fields:
            if field.mode & constants.AccessMode.LOAD:
                value = field.load(data, self)

                if value is not ...:
                    data[field.origin] = value

    def dict(self, strip_none=False):
        data = self._data.copy()

        for name, field in self.__fields__.items():
            if field.mode & constants.AccessMode.DUMP:
                value = getattr(self, name)
                data.pop(field.origin, None)

                if strip_none and value is None:
                    continue

                if isinstance(field, Nested) and value is not None:
                    if field.many:
                        value = [item.dict(strip_none=strip_none) for item in value]
                    else:
                        value = value.dict(strip_none=strip_none)

                data[field.destination] = value

        return data
