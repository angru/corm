import ast
import sys
import typing as t
import warnings
from collections.abc import Hashable, Iterable
from types import EllipsisType, NoneType, UnionType
from weakref import getweakrefcount

from corm import registry
from corm.constants import AccessMode, RelationType
from corm.exceptions import (
    ConfigurationError,
    EntityNotFoundError,
    MissingFieldError,
    ReadOnlyFieldError,
    RegistryError,
    RelationError,
)

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


def _annotation_entity_type(target):
    from corm.entity import Entity

    target = _annotation_expression(target)
    if isinstance(target, ast.expr):
        return _annotation_name(target)
    if isinstance(target, type) and issubclass(target, Entity):
        return target
    return None


def proxy_factory(value: t.Any) -> t.Callable[[], t.Any]:
    def proxy():
        return value

    return proxy


class KeyManager:
    def get(self, data: t.Any) -> Hashable:
        raise NotImplementedError

    def prepare_to_set(self, entity: "Entity | None") -> t.Any:
        raise NotImplementedError


class DefaultKeyManager(KeyManager):
    def __init__(self, field: "Field") -> None:
        self.field = field

    def get(self, data: t.Any) -> Hashable:
        return data

    def prepare_to_set(self, entity: "Entity | None") -> t.Any:
        if entity:
            return getattr(entity, self.field.name)


_RelationParams = t.ParamSpec("_RelationParams")


def _apply_relation(
    field: "Field | None",
    operation: t.Callable[_RelationParams, None],
    /,
    *args: _RelationParams.args,
    **kwargs: _RelationParams.kwargs,
) -> None:
    try:
        operation(*args, **kwargs)
    except RelationError as error:
        if field is None:
            raise
        raise RelationError(f"{field}: {error}") from error


class RelationshipList(list["Entity"]):
    def __init__(
        self,
        entity: "Entity",
        items: Iterable["Entity"],
        relation_type: Hashable = None,
        *,
        field: "Field | None" = None,
    ) -> None:
        super().__init__(items)

        self.entity = entity
        self.relation_type = relation_type
        self._field = field

    def _relation_endpoints(self, entity: "Entity") -> "tuple[Entity, Entity]":
        return self.entity, entity

    def make_relation(self, entity: "Entity") -> None:
        source, target = self._relation_endpoints(entity)
        _apply_relation(
            self._field,
            self.entity.storage.make_relation,
            from_=source,
            to_=target,
            relation_type=self.relation_type,
        )

    def remove_relation(self, entity: "Entity") -> None:
        source, target = self._relation_endpoints(entity)
        _apply_relation(
            self._field,
            self.entity.storage.remove_relation,
            from_=source,
            to_=target,
            relation_type=self.relation_type,
        )

    def append(self, entity: "Entity") -> None:
        if self.relation_type:
            self.make_relation(entity)
        super().append(entity)

    def extend(self, entities: Iterable["Entity"]) -> None:
        for entity in entities:
            self.append(entity)

    def remove(self, entity: "Entity") -> None:
        try:
            index = self.index(entity)
        except ValueError as error:
            relation = self._field or f"Relation type {self.relation_type!r}"
            raise RelationError(
                f"{relation} does not exist between "
                f"{type(self.entity).__name__} and {type(entity).__name__}"
            ) from error

        if self.relation_type:
            self.remove_relation(self[index])
        super().__delitem__(index)

    def insert(self, index: t.SupportsIndex, entity: "Entity") -> None:
        raise NotImplementedError

    def pop(self, index: t.SupportsIndex = -1) -> "Entity":
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
        items: Iterable["Entity"],
        relation_type: Hashable = None,
        *,
        field: "Field | None" = None,
    ) -> None:
        super().__init__(
            entity=entity,
            items=items,
            relation_type=relation_type,
            field=field,
        )

        if relation_type:
            for item in self:
                self.make_relation(item)

    def _relation_endpoints(self, entity: "Entity") -> "tuple[Entity, Entity]":
        return entity, self.entity


_CAN_REUSE_LIST = (
    sys.implementation.name == "cpython"
    and getattr(sys, "_is_gil_enabled", lambda: True)()
)


class _PairedList(list["Entity"]):
    @classmethod
    def _get(cls, field, entity):
        if not _CAN_REUSE_LIST:
            return cls(field._read_paired_list(entity), field, entity)

        views = entity._paired_list_views
        if views is None:
            entity._paired_list_views = views = {}

        # Detach the slot before checking ownership. The only allowed references
        # are the slot itself and the reference passed to getrefcount.
        slot = views.pop(field, None)
        if (
            slot is None
            or sys.getrefcount(slot[0]) != 2
            or getweakrefcount(slot[0])
            or not slot[0]._is_current()
        ):
            slot = (cls(field._read_paired_list(entity), field, entity),)
        view = slot[0]
        views[field] = slot
        return view

    def __init__(self, items, field, entity):
        super().__init__(items)
        self._field = field
        self.entity = entity
        self._remember_revision()

    def _remember_revision(self):
        self._revision = self._field._list_revision(self.entity, len(self))

    def _is_current(self):
        return self._revision == self._field._list_revision(self.entity, len(self))

    def _current_items(self):
        # Only the edited snapshot is refreshed after changes through another view.
        if self._is_current():
            return self
        return list(self._field._read_paired_list(self.entity))

    def _edit(self, operation, *args, **kwargs):
        field, entity = self._field, self.entity
        items = list(field._read_paired_list(entity))
        result = operation(items, *args, **kwargs)
        field._write_paired_list(entity, items)
        list.__setitem__(self, slice(None), field._read_paired_list(entity))
        self._remember_revision()
        return result

    def _belongs_to(self, field, entity):
        return self._field is field and self.entity is entity

    def append(self, entity):
        items = self._current_items()
        added = self._field._append_paired_item(self.entity, entity)
        if items is not self:
            list.__setitem__(self, slice(None), items)
        if added:
            list.append(self, entity)
        self._remember_revision()

    def extend(self, entities):
        self._edit(list.extend, entities)

    def remove(self, entity):
        items = self._current_items()
        try:
            index = items.index(entity)
        except ValueError as error:
            raise RelationError(f"Relation does not exist for {self._field}") from error
        self._field._remove_paired_item(self.entity, items[index])
        if items is not self:
            list.__setitem__(self, slice(None), items)
        list.__delitem__(self, index)
        self._remember_revision()

    def clear(self):
        self._edit(list.clear)

    def insert(self, index, entity):
        self._edit(list.insert, index, entity)

    def pop(self, index=-1):
        return self._edit(list.pop, index)

    def __setitem__(self, index, value):
        self._edit(list.__setitem__, index, value)

    def __delitem__(self, index):
        self._edit(list.__delitem__, index)

    # list.__add__ can widen its element type. In-place edits keep Entity items.
    def __iadd__(self, entities: Iterable["Entity"], /) -> t.Self:  # type: ignore[override, misc]
        self._edit(list.__iadd__, entities)
        return self

    def __imul__(self, count: t.SupportsIndex, /) -> t.Self:
        self._edit(list.__imul__, count)
        return self

    def reverse(self):
        self._edit(list.reverse)

    def sort(self, *, key=None, reverse=False):
        self._edit(list.sort, key=key, reverse=reverse)


class _ReverseList(_PairedList, RelationshipList):
    def __init__(self, items, field, entity):
        RelationshipList.__init__(self, entity, items, field.relation_type, field=field)
        self._remember_revision()

    def append(self, entity):
        if self._field._owning_field is None:
            RelationshipList.append(self, entity)
        else:
            super().append(entity)

    def remove(self, entity):
        if self._field._owning_field is None:
            RelationshipList.remove(self, entity)
        else:
            super().remove(entity)

    def extend(self, entities):
        if self._field._owning_field is not None:
            super().extend(list(entities))
            return

        remaining = iter(entities)
        for owner in remaining:
            # Advancing the iterator may have constructed the first owner.
            if self._field._owning_field is not None:
                super().extend([owner, *remaining])
                return
            RelationshipList.append(self, owner)

    def __iadd__(self, entities: Iterable["Entity"], /) -> t.Self:  # type: ignore[override, misc]
        return super().__iadd__(list(entities))

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            value = list(value)
        super().__setitem__(index, value)

    def _edit(self, operation, *args, **kwargs):
        # The first owner may have been constructed after this list was read.
        if self._field._owning_field is None:
            legacy_operation = getattr(RelationshipList, operation.__name__)
            return legacy_operation(self, *args, **kwargs)
        return super()._edit(operation, *args, **kwargs)


class Field:
    name: str
    _declaring_owner: type["Entity"]
    pk: bool
    mode: AccessMode
    default: t.Callable[[], t.Any] | EllipsisType
    origin: str | None
    destination: str | None

    def __init__(
        self,
        pk: bool = False,
        mode: AccessMode = AccessMode.ALL,
        default: t.Any = ...,
        origin: str | None = None,
        destination: str | None = None,
    ) -> None:
        self.pk = pk
        self.mode = mode
        self.origin = origin
        self.destination = destination

        if default is not ... and not callable(default):
            default = proxy_factory(default)

        self.default = default

    def __get__(self, instance: "Entity", owner) -> t.Any:
        if instance:
            return instance._data.get(t.cast(str, self.origin))
        else:
            return self

    def __set__(self, instance: "Entity", value: t.Any) -> None:
        if not instance:
            raise ReadOnlyFieldError(f"Not able to change {self} on class")
        self._check_writable(instance)
        if self.pk:
            instance.storage._set_primary_key(instance, self, value)
        else:
            instance._data[t.cast(str, self.origin)] = value

    def _check_writable(self, instance: "Entity") -> None:
        if not self.mode & AccessMode.SET:
            raise ReadOnlyFieldError(
                f"Field '{self.name}' is read only on {type(instance).__name__}"
            )

    def __set_name__(self, owner, name):
        # EntityMeta reattaches inherited fields when defining subclasses.
        if not hasattr(self, "_declaring_owner"):
            self._declaring_owner = owner
        self.name = name
        self.owner = owner

        if self.origin is None:
            self.origin = name

        if self.destination is None:
            self.destination = self.origin

    def load(self, data: dict[str, t.Any], instance: "Entity") -> t.Any:
        value = data.get(t.cast(str, self.origin), ...)

        if value is ...:
            if callable(self.default):
                return self.default()
            else:
                raise MissingFieldError(
                    f"No value for field '{self.name}' of entity: {type(instance)}",
                )

        return value

    def __repr__(self) -> str:
        if not hasattr(self, "owner"):
            return f"<{type(self).__name__}>"
        return f"<Field[{self.owner.__name__}.{self.name}]>"


class _RelationField(Field):
    many: bool | None

    def _infer_from_annotation(self, annotation, field_name: str) -> None:
        if self.many is None:
            _, self.many = _annotation_parts(annotation)


class _EntityRelationField(_RelationField):
    _entity_type: str | type["Entity"] | None
    _entity_type_name: str | None = None

    def _infer_from_annotation(self, annotation, field_name: str) -> None:
        if self._entity_type is not None:
            super()._infer_from_annotation(annotation, field_name)
            return

        if annotation is ...:
            raise ConfigurationError(
                f"{field_name} requires an entity_type or annotation"
            )

        target, many = _annotation_parts(annotation)
        target = _annotation_entity_type(target)
        if target is None:
            raise ConfigurationError(
                f"Unsupported relation annotation for {field_name}"
            )

        self._entity_type = target
        if self.many is None:
            self.many = many

    @property
    def entity_type(self) -> type["Entity"]:
        entity_type = self._entity_type
        resolved = self._resolve_entity_type(entity_type)
        if isinstance(entity_type, str):
            self._entity_type_name = entity_type
            self._entity_type = resolved
        return resolved

    def _resolve_entity_type(
        self, entity_type: str | type["Entity"] | None
    ) -> type["Entity"]:
        if isinstance(entity_type, str):
            try:
                entity_type = registry.get(entity_type)
            except RegistryError as error:
                if not hasattr(self, "owner"):
                    raise
                field_name = f"{self.owner.__name__}.{self.name}"
                raise RegistryError(f"{field_name}: {error}") from error
        if entity_type is None:
            raise ConfigurationError(f"{self} requires an entity_type or annotation")
        return entity_type


class _OwningRelationField(_RelationField):
    def __init__(self, *, back_relation, back_populates, **options):
        super().__init__(**options)
        if back_relation:
            if back_populates is not None:
                raise ConfigurationError(
                    "Use either back_populates or back_relation "
                    f"(back_populates={back_populates!r})"
                )
            warnings.warn(
                "back_relation is deprecated. Use back_populates instead.",
                DeprecationWarning,
                stacklevel=3,
            )
            if back_relation is True:
                back_relation = RelationType.RELATED

        self.back_relation = back_relation
        self.back_populates = back_populates
        self._relationship = None

    def _resolve_pair(self):
        if self._relationship is not None:
            return self._relationship

        owner_name = f"{self._declaring_owner.__name__}.{self.name}"
        try:
            target = self.entity_type
        except (RegistryError, ConfigurationError) as error:
            target_name = getattr(self._entity_type, "__name__", self._entity_type)
            raise type(error)(
                f"{owner_name} cannot pair with "
                f"{target_name}.{self.back_populates}: {error.args[0]}"
            ) from error

        target_name = f"{target.__name__}.{self.back_populates}"
        pair_name = f"{owner_name} and {target_name}"
        relationship = getattr(target, self.back_populates, ...)
        if relationship is ...:
            raise ConfigurationError(
                f"Cannot pair {pair_name}: {target_name} does not exist"
            )
        if not isinstance(relationship, Relationship):
            raise ConfigurationError(
                f"Cannot pair {pair_name}: {target_name} is not a Relationship"
            )
        other = relationship._owning_field
        owner = self._declaring_owner
        entity_type_name = None
        if other is not None:
            other_owner = other._declaring_owner
            if (
                other_owner is owner
                or other_owner.__module__ != owner.__module__
                or other_owner.__qualname__ != owner.__qualname__
                or other.name != self.name
            ):
                raise ConfigurationError(
                    f"Cannot pair {pair_name}: already paired with "
                    f"{other_owner.__name__}.{other.name}"
                )
            entity_type_name = relationship._entity_type_name
        try:
            if entity_type_name is None:
                related_type = relationship.entity_type
            else:
                related_type = relationship._resolve_entity_type(entity_type_name)
        except RegistryError as error:
            raise RegistryError(f"Cannot pair {pair_name}: {error}") from error
        if not issubclass(owner, related_type):
            raise ConfigurationError(
                f"Cannot pair {pair_name}: "
                f"{target_name} refers to {related_type.__name__}"
            )

        if entity_type_name is not None:
            relationship._entity_type = related_type
        relationship._owning_field = self
        self._relationship = relationship
        return relationship

    def _check_owner(self, owner: "Entity") -> None:
        self._check_writable(owner)
        declaring_owner = self._declaring_owner
        if not isinstance(owner, declaring_owner) or (
            getattr(type(owner), self.name, None) is not self
        ):
            raise RelationError(
                f"Expected an owner of {declaring_owner.__name__}.{self.name}"
            )

    def _prepare_target(self, owner, target):
        self._check_target_relationship(target)
        if target.storage is not owner.storage:
            raise RelationError(
                f"Related entities for {self} must use the same storage"
            )
        return target

    def _check_target_relationship(self, target):
        entity_type = self.entity_type
        if not isinstance(target, entity_type):
            raise RelationError(f"Expected {entity_type.__name__} for {self}")
        target_type = type(target)
        if getattr(target_type, self.back_populates, None) is not self._resolve_pair():
            raise RelationError(
                f"{self._declaring_owner.__name__}.{self.name} requires its paired "
                f"Relationship on {target_type.__name__}.{self.back_populates}"
            )

    def _source(self, item):
        return item

    def _source_for_target(self, target):
        return target

    def _items(self, data):
        if data is None:
            return ()
        return data if self.many else (data,)

    def _list_revision(self, owner, size):
        return owner._paired_list_revisions.get(self, 0)

    def _mark_list_changed(self, owner):
        if self.many:
            revisions = owner._paired_list_revisions
            revisions[self] = revisions.get(self, 0) + 1

    def _append_paired_item(self, owner, target):
        self._link(owner, self._prepare_target(owner, target))
        return True

    def _remove_paired_item(self, owner, target):
        self._unlink(owner, self._source_for_target(target))

    def _replace_paired_data(self, owner, data, *, loading=False):
        relationship = self._resolve_pair()
        if not loading:
            self._check_owner(owner)
        old_data = None if loading else owner._data.get(self.origin)
        old_sources = {self._source(item) for item in self._items(old_data)}
        sources = [self._source(item) for item in self._items(data)]
        new_sources = set(sources)
        if len(new_sources) != len(sources):
            raise RelationError(f"Duplicate entities for {self}")

        added = [source for source in sources if source not in old_sources]
        storage = owner.storage
        if not relationship.many:
            moves = []
            for source in added:
                old_owner = storage.get_one_related_entity(
                    source, self._declaring_owner, self
                )
                if old_owner is not None:
                    self._check_owner(old_owner)
                    moves.append((old_owner, source))
            for old_owner, source in moves:
                self._unlink(old_owner, source)

        for source in old_sources - new_sources:
            storage.remove_relation(source, owner, self)
        for source in added:
            storage.make_relation(source, owner, self)
        if not loading:
            owner._data[self.origin] = data
            self._mark_list_changed(owner)

    def _unlink(self, owner, source):
        self._check_owner(owner)
        data = owner._data.get(self.origin)
        if self.many:
            for index, item in enumerate(data or ()):
                if self._source(item) == source:
                    owner.storage.remove_relation(source, owner, self)
                    del data[index]
                    break
            else:
                raise RelationError(f"Relation does not exist for {self}")
        else:
            owner.storage.remove_relation(source, owner, self)
            owner._data[self.origin] = None
        self._mark_list_changed(owner)

    def _link(self, owner, item):
        if not self.many:
            self._replace_paired_data(owner, item)
            return

        from corm.storage import _relation_key

        self._check_owner(owner)
        source = self._source(item)
        storage = owner.storage
        relationship = self._resolve_pair()
        bucket = storage._get_relation_bucket(source, self._declaring_owner, self)
        if _relation_key(owner) in bucket:
            raise RelationError(f"Duplicate entities for {self}")
        if not relationship.many:
            old_owner = next(iter(bucket.values()), None)
            if old_owner is not None:
                self._unlink(old_owner, source)

        storage.make_relation(source, owner, self)
        data = owner._data.get(self.origin)
        if data is None:
            owner._data[self.origin] = [item]
        else:
            data.append(item)
        self._mark_list_changed(owner)

    def _set_paired_value(self, owner, value):
        if self.many:
            value = [self._prepare_target(owner, item) for item in value]
        elif value is not None:
            value = self._prepare_target(owner, value)
        self._replace_paired_data(owner, value)


class Nested(_EntityRelationField, _OwningRelationField):
    def __init__(
        self,
        entity_type: str | type["Entity"] | None = None,
        many: bool | None = None,
        back_relation: Hashable = False,
        mode: AccessMode = AccessMode.ALL,
        default: t.Any = ...,
        origin: str | None = None,
        destination: str | None = None,
        *,
        back_populates: str | None = None,
    ):
        super().__init__(
            back_relation=back_relation,
            back_populates=back_populates,
            mode=mode,
            default=default,
            origin=origin,
            destination=destination,
        )

        self._entity_type = entity_type
        self.many = many

    def _load_one(self, data: t.Any, storage: "Storage", parent: "Entity"):
        entity = self.entity_type(data=data, storage=storage)

        return entity

    def load(self, data: dict[str, t.Any], instance: "Entity") -> t.Any:
        value = super().load(data, instance)
        storage = instance.storage

        if self.many:
            items = (self.entity_type(data=item, storage=storage) for item in value)
            if self.back_populates is None:
                return NestedList(
                    entity=instance,
                    items=items,
                    relation_type=self.back_relation,
                    field=self,
                )
            value = list(items)

        elif value is not None:
            value = self.entity_type(data=value, storage=storage)

            if self.back_relation:
                _apply_relation(
                    self,
                    storage.make_relation,
                    from_=value,
                    to_=instance,
                    relation_type=self.back_relation,
                )

        if self.back_populates is not None:
            self._replace_paired_data(instance, value, loading=True)
        return value

    def __get__(self, instance: "Entity", owner):
        if instance and self.many and self.back_populates is not None:
            return _PairedList._get(self, instance)
        return super().__get__(instance, owner)

    def _read_paired_list(self, instance):
        return instance._data.get(self.origin) or ()

    _write_paired_list = _OwningRelationField._set_paired_value

    def __set__(
        self,
        instance: "Entity",
        value: "list[Entity] | Entity | None",
    ) -> None:
        if not instance:
            return super().__set__(instance, value)
        self._check_writable(instance)

        if self.many and not isinstance(value, list):
            raise RelationError(
                "Only list accepted for nested field with many set to True, "
                f"got {value} for {self}"
            )

        if self.back_populates is not None:
            self._set_paired_value(instance, value)
            return

        old_value = getattr(instance, t.cast(str, self.origin))
        if self.many:
            items = list(t.cast("list[Entity]", value))
            old_value.clear()

            value = NestedList(
                entity=instance,
                items=items,
                relation_type=self.back_relation,
                field=self,
            )
        else:
            if self.back_relation and old_value is not None:
                _apply_relation(
                    self,
                    instance.storage.remove_relation,
                    from_=old_value,
                    to_=instance,
                    relation_type=self.back_relation,
                )

            if self.back_relation and value is not None:
                _apply_relation(
                    self,
                    instance.storage.make_relation,
                    from_=t.cast("Entity", value),
                    to_=instance,
                    relation_type=self.back_relation,
                )

        super().__set__(instance, value)


class Relationship(_EntityRelationField):
    def __init__(
        self,
        entity_type: str | type["Entity"] | None = None,
        relation_type: Hashable = RelationType.RELATED,
        many: bool | None = None,
    ):
        super().__init__(mode=AccessMode.GET | AccessMode.SET)

        self._entity_type = entity_type
        self.relation_type = relation_type
        self.many = many
        self._owning_field = None

    def _list_revision(self, target, size):
        field = self._owning_field
        if field is not None:
            source = field._source_for_target(target)
            bucket = target.storage._get_relation_bucket(
                source, field._declaring_owner, field
            )
            return field, source, bucket.revision

    def _append_paired_item(self, target, owner):
        from corm.storage import _relation_key

        field = self._owning_field
        source = field._source_for_target(target)
        bucket = target.storage._get_relation_bucket(
            source, field._declaring_owner, field
        )
        if _relation_key(owner) in bucket:
            return False
        self._check_paired_owner(target, owner)
        field._link(owner, field._prepare_target(owner, target))
        return True

    def _remove_paired_item(self, target, owner):
        field = self._owning_field
        self._check_paired_owner(target, owner)
        field._unlink(owner, field._source_for_target(target))

    def _check_paired_owner(self, target, owner):
        self._owning_field._check_owner(owner)
        if owner.storage is not target.storage:
            raise RelationError(
                f"Related entities for {self} must use the same storage"
            )

    def _read_paired_list(self, instance):
        field = self._owning_field
        return instance.storage.get_related_entities(
            field._source_for_target(instance), field._declaring_owner, field
        )

    def __get__(self, instance: "Entity", owner):
        if not instance:
            return super().__get__(instance, owner)

        field = self._owning_field
        if self.many:
            if field is not None:
                return _ReverseList._get(self, instance)
            entities = instance.storage.get_related_entities(
                instance, self.entity_type, self.relation_type
            )
            return _ReverseList(entities, self, instance)

        if field is not None:
            return instance.storage.get_one_related_entity(
                field._source_for_target(instance), field._declaring_owner, field
            )

        return instance.storage.get_one_related_entity(
            instance, self.entity_type, self.relation_type
        )

    def __set__(self, instance, value):
        if not instance:
            return super().__set__(instance, value)
        self._check_writable(instance)

        if self._owning_field is not None:
            self._set_paired_owners(instance, value)
            return

        instance.storage.remove_relations(
            instance,
            self.entity_type,
            self.relation_type,
        )

        if value:
            if self.many:
                remaining = iter(value)
                for entity in remaining:
                    # Advancing the iterator can construct the first owner.
                    if self._owning_field is not None:
                        self._set_paired_owners(instance, [entity, *remaining])
                        return
                    _apply_relation(
                        self,
                        instance.storage.make_relation,
                        from_=instance,
                        to_=entity,
                        relation_type=self.relation_type,
                    )
            else:
                _apply_relation(
                    self,
                    instance.storage.make_relation,
                    from_=instance,
                    to_=value,
                    relation_type=self.relation_type,
                )

    def _set_paired_owners(self, target, value):
        from corm.storage import _relation_key

        field = self._owning_field
        if value is None:
            owners = {}
        else:
            owners = {
                _relation_key(owner): owner
                for owner in (value if self.many else (value,))
            }
        current = {
            _relation_key(owner): owner for owner in self._read_paired_list(target)
        }
        added = [owner for key, owner in owners.items() if key not in current]
        removed = [owner for key, owner in current.items() if key not in owners]
        for owner in added + removed:
            self._check_paired_owner(target, owner)
        prepared = [(owner, field._prepare_target(owner, target)) for owner in added]

        source = field._source_for_target(target)
        # A single reverse link is moved by the owning field when it attaches.
        if self.many or not added:
            for owner in removed:
                field._unlink(owner, source)
        for owner, item in prepared:
            field._link(owner, item)

        if self.many:
            current_order = [key for key in current if key in owners]
            current_order.extend(key for key in owners if key not in current)
            if current_order != list(owners):
                target.storage._reorder_relations(source, field, owners.values())

    _write_paired_list = _set_paired_owners


class KeyNested(_EntityRelationField, _OwningRelationField):
    def __init__(
        self,
        related_entity_field: object,
        back_relation: Hashable = False,
        many: bool | None = None,
        mode: AccessMode = AccessMode.GET_SET_LOAD,
        default: t.Any = ...,
        origin: str | None = None,
        destination: str | None = None,
        key_manager: KeyManager | None = None,
        required: bool = True,
        *,
        back_populates: str | None = None,
    ):
        if not isinstance(related_entity_field, Field) or not related_entity_field.pk:
            raise ConfigurationError(
                f"'{related_entity_field}' is not primary key field",
            )

        super().__init__(
            back_relation=back_relation,
            back_populates=back_populates,
            mode=mode,
            origin=origin,
            destination=destination,
            default=default,
        )

        self.related_entity_field = related_entity_field
        self.key_manager = key_manager or DefaultKeyManager(
            field=related_entity_field,
        )
        self._entity_type = None
        self.many = many
        self.required = required

    def _infer_from_annotation(self, annotation, field_name: str) -> None:
        if self.back_populates is None:
            return _RelationField._infer_from_annotation(self, annotation, field_name)

        target, many = _annotation_parts(annotation)
        self._entity_type = _annotation_entity_type(target)
        if self.many is None:
            self.many = many

    @property
    def entity_type(self):
        key_field = self.related_entity_field
        if self.back_populates is None:
            return key_field.owner
        if self._entity_type is None:
            return key_field._declaring_owner

        # Subclasses can share a key descriptor but have different reverse fields.
        target = super().entity_type
        if key_field not in (target.__pk_fields__ or ()):
            raise ConfigurationError(
                f"{self}: {target.__name__} does not use {key_field.name} as its key"
            )
        return target

    def _prepare_target(self, owner, target):
        super()._prepare_target(owner, target)
        data = self.key_manager.prepare_to_set(target)
        if data is None and not self.many:
            raise RelationError(f"Expected a non-null key for {self}")
        key = self.key_manager.get(data)
        if owner.storage.get(self.related_entity_field, key) is not target:
            raise RelationError(f"Expected a stored target for {self}")
        return data

    def _source(self, item):
        return self._key_source(self.key_manager.get(item))

    def _source_for_target(self, target):
        if isinstance(target, self.entity_type):
            key = getattr(target, self.related_entity_field.name)
            if target.storage.get(self.related_entity_field, key) is target:
                return self._key_source(key)

    def _key_source(self, key):
        from corm.storage import EntityRef

        # Paired links follow the stored key, even if an entity changes its PK.
        # Using this field keeps these buckets out of the PK index migration.
        return EntityRef(self, key)

    def _lookup_target(self, storage, key):
        target = storage.get(self.related_entity_field, key)
        if self.back_populates is not None and target is not None:
            self._check_target_relationship(target)
        return target

    def _load_one(self, data: Hashable, storage: "Storage", parent: "Entity") -> None:
        if self.back_relation:
            _apply_relation(
                self,
                storage.make_key_relation,
                field_from=self.related_entity_field,
                key_from=data,
                relation_type=self.back_relation,
                to=parent,
            )

    def load(self, data: dict[str, t.Any], instance: "Entity") -> t.Any:
        storage = instance.storage
        value = super().load(data, instance)

        if self.back_populates is not None:
            if self.many and value is not None:
                value = list(value)
            for item in self._items(value):
                self._lookup_target(storage, self.key_manager.get(item))
            self._replace_paired_data(instance, value, loading=True)
            return value

        if value is None:
            return None

        if self.many:
            for item in value:
                key = self.key_manager.get(item)
                self._load_one(key, storage, instance)
        else:
            key = self.key_manager.get(value)
            self._load_one(key, storage, instance)

        return value

    def __get__(self, instance: "Entity", owner):
        data = super().__get__(instance, owner)

        if not instance or data is None:
            return data

        if self.many:
            if self.back_populates is not None:
                return _PairedList._get(self, instance)
            return self._get_many(instance)
        else:
            key = self.key_manager.get(data)
            entity = self._lookup_target(instance.storage, key)

            if not entity and self.required:
                raise EntityNotFoundError(
                    f"{self}: Can't find {self.related_entity_field}={key} in storage"
                )

            return entity

    def _list_revision(self, owner, size):
        storage = owner.storage
        # Registering a target can only change a snapshot with unresolved keys.
        pending = len(owner._data.get(self.origin) or ()) != size
        return (
            super()._list_revision(owner, size),
            storage._key_moves,
            storage._key_additions if pending else None,
        )

    def _get_many(self, instance):
        result = []
        for item in instance._data.get(self.origin) or ():
            key = self.key_manager.get(item)
            entity = self._lookup_target(instance.storage, key)
            if entity:
                result.append(entity)
            elif self.required:
                raise EntityNotFoundError(
                    f"{self}: Can't find {self.related_entity_field}={key} in storage"
                )
        return result

    _read_paired_list = _get_many

    def _write_paired_list(self, instance, entities):
        items = [self._prepare_target(instance, entity) for entity in entities]
        positions = {
            self.key_manager.get(item): index for index, item in enumerate(items)
        }
        pending = {}
        next_index = 0

        # List edits preserve unresolved keys and the raw data for retained keys.
        for item in instance._data.get(self.origin) or ():
            key = self.key_manager.get(item)
            if key in positions:
                index = positions[key]
                items[index] = item
                next_index = index + 1
            elif self._lookup_target(instance.storage, key) is None:
                pending.setdefault(next_index, []).append(item)

        for index, values in sorted(pending.items(), reverse=True):
            items[index:index] = values
        self._replace_paired_data(instance, items)

    def __set__(
        self,
        instance: "Entity",
        value: "Entity | list[Entity] | None",
    ) -> None:
        if not instance:
            return super().__set__(instance, value)
        self._check_writable(instance)

        if self.back_populates is not None:
            if isinstance(value, _PairedList) and value._belongs_to(self, instance):
                self._write_paired_list(instance, value)
            else:
                self._set_paired_value(instance, value)
            return

        if self.many:
            if self.back_relation:
                for old_related_entity in getattr(instance, self.name):
                    _apply_relation(
                        self,
                        instance.storage.remove_relation,
                        from_=old_related_entity,
                        to_=instance,
                        relation_type=self.back_relation,
                    )

            new_data = []

            for related_entity in t.cast("list[Entity]", value):
                new_data.append(self.key_manager.prepare_to_set(related_entity))

                if self.back_relation:
                    _apply_relation(
                        self,
                        instance.storage.make_relation,
                        from_=related_entity,
                        to_=instance,
                        relation_type=self.back_relation,
                    )

        else:
            if self.back_relation:
                old_related_entity = getattr(instance, self.name)

                if old_related_entity:
                    _apply_relation(
                        self,
                        instance.storage.remove_relation,
                        from_=old_related_entity,
                        to_=instance,
                        relation_type=self.back_relation,
                    )

            related = t.cast("Entity | None", value)
            new_data = self.key_manager.prepare_to_set(related)

            if self.back_relation:
                _apply_relation(
                    self,
                    instance.storage.make_relation,
                    from_=t.cast("Entity", related),
                    to_=instance,
                    relation_type=self.back_relation,
                )

        super().__set__(instance, new_data)
