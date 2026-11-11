import ast
import typing as t
from types import NoneType, UnionType

from corm import registry
from corm.constants import AccessMode, RelationType

if t.TYPE_CHECKING:
    from corm.entity import Entity
    from corm.storage import Storage


def _annotation_expression(annotation):
    if isinstance(annotation, t.ForwardRef):
        annotation = annotation.__forward_arg__

    # Postponed annotations can contain a second layer of quotes.
    while True:
        if isinstance(annotation, ast.Constant):
            annotation = annotation.value
        elif isinstance(annotation, str):
            try:
                annotation = ast.parse(annotation.strip(), mode="eval").body
            except SyntaxError:
                return None
        else:
            return annotation


def _annotation_name(expression):
    if isinstance(expression, ast.Name):
        return expression.id
    if isinstance(expression, ast.Attribute):
        prefix = _annotation_name(expression.value)
        if prefix is not None:
            return f"{prefix}.{expression.attr}"
    return None


def _annotation_parts(annotation):
    """Return the target expression and whether the relation is a list."""
    annotation = _annotation_expression(annotation)
    if isinstance(annotation, ast.expr):
        match annotation:
            case (
                ast.BinOp(left=ast.Constant(value=None), op=ast.BitOr(), right=target)
                | ast.BinOp(left=target, op=ast.BitOr(), right=ast.Constant(value=None))
            ):
                return _annotation_parts(target)
            case ast.Subscript(value=alias, slice=item):
                match _annotation_name(alias):
                    case "Optional" | "typing.Optional":
                        return _annotation_parts(item)
                    case "list" | "List" | "typing.List":
                        return item, True
            case _:
                if _annotation_name(annotation) in {"list", "List", "typing.List"}:
                    return None, True
        return annotation, False

    origin = t.get_origin(annotation)
    args = t.get_args(annotation)
    if origin is list or annotation is list:
        return (args[0] if len(args) == 1 else None), True
    if origin in (t.Union, UnionType) and len(args) == 2 and NoneType in args:
        target = next(arg for arg in args if arg is not NoneType)
        return _annotation_parts(target)
    return annotation, False


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

    def extend(self, entities: list["Entity"]) -> None:
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


class Field:
    name: str
    pk: bool
    mode: int
    default: t.Callable[[], t.Any]
    origin: str | None
    destination: str | None

    def __init__(
        self,
        pk: bool = False,
        mode: AccessMode = AccessMode.ALL,
        default: t.Any | t.Callable[[], t.Any] = ...,
        origin: str | None = None,
        destination: str | None = None,
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
                if self.pk:
                    instance.storage._set_primary_key(instance, self, value)
                else:
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


class _RelationField(Field):
    many: bool | None

    def _infer_from_annotation(self, annotation, field_name: str) -> None:
        if self.many is None:
            _, self.many = _annotation_parts(annotation)


class _EntityRelationField(_RelationField):
    _entity_type: str | type["Entity"] | None

    def _infer_from_annotation(self, annotation, field_name: str) -> None:
        if self._entity_type is not None:
            super()._infer_from_annotation(annotation, field_name)
            return

        from corm.entity import Entity

        if annotation is ...:
            raise ValueError(f"{field_name} requires an entity_type or annotation")

        target, many = _annotation_parts(annotation)
        target = _annotation_expression(target)
        if isinstance(target, ast.expr):
            target = _annotation_name(target)

        if not (
            isinstance(target, str)
            or (isinstance(target, type) and issubclass(target, Entity))
        ):
            raise ValueError(f"Unsupported relation annotation for {field_name}")

        self._entity_type = target
        if self.many is None:
            self.many = many

    @property
    def entity_type(self) -> type["Entity"]:
        entity_type = self._entity_type
        if isinstance(entity_type, str):
            try:
                entity_type = registry.get(entity_type)
            except (KeyError, ValueError) as error:
                if not hasattr(self, "owner"):
                    raise
                field_name = f"{self.owner.__name__}.{self.name}"
                raise type(error)(f"{field_name}: {error.args[0]}") from error
            self._entity_type = entity_type
        return entity_type


class Nested(_EntityRelationField):
    def __init__(
        self,
        entity_type: str | type["Entity"] | None = None,
        many: bool | None = None,
        back_relation: t.Any = False,
        mode: AccessMode = AccessMode.ALL,
        default: t.Any | t.Callable[[], t.Any] = ...,
        origin: str | None = None,
        destination: str | None = None,
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

        elif data is not None:
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
        value: "list[Entity] | Entity",
    ):
        if not instance:
            return super().__set__(instance, value)

        old_value = getattr(instance, self.origin)

        if self.many:
            if not isinstance(value, list):
                raise ValueError(
                    "Only list accepted for nested field with many set to True, "
                    f"got: {value}",
                )

            value = list(value)
            old_value.clear()

            value = NestedList(
                entity=instance,
                items=value,
                relation_type=self.back_relation,
            )
        else:
            if self.back_relation and old_value is not None:
                instance.storage.remove_relation(
                    from_=old_value,
                    to_=instance,
                    relation_type=self.back_relation,
                )

            if self.back_relation and value is not None:
                instance.storage.make_relation(
                    from_=value,
                    to_=instance,
                    relation_type=self.back_relation,
                )

        super().__set__(instance, value)


class Relationship(_EntityRelationField):
    def __init__(
        self,
        entity_type: str | type["Entity"] | None = None,
        relation_type: t.Any = RelationType.RELATED,
        many: bool | None = None,
    ):
        super().__init__(mode=AccessMode.GET)

        self._entity_type = entity_type
        self.relation_type = relation_type
        self.many = many

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


class KeyNested(_RelationField):
    def __init__(
        self,
        related_entity_field: Field | t.Any,
        back_relation: t.Any = False,
        many: bool | None = None,
        mode: AccessMode = AccessMode.GET_SET_LOAD,
        default: t.Any | t.Callable[[], t.Any] = ...,
        origin: str | None = None,
        destination: str | None = None,
        key_manager: KeyManager | None = None,
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
                            f"Can't find {self.related_entity_field}={key} in storage",
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
                    f"Can't find {self.related_entity_field}={key} in storage",
                )

            return entity

    def __set__(
        self,
        instance: "Entity",
        value: "Entity | list[Entity]",
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
