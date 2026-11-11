import ast
import typing as t
import warnings
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


class _PairedList(list):
    def __init__(self, items, field, entity):
        super().__init__(items)
        self._field = field
        self.entity = entity

    def _edit(self, operation, *args, **kwargs):
        field, entity = self._field, self.entity
        items = list(field._read_paired_list(entity))
        result = operation(items, *args, **kwargs)
        field._write_paired_list(entity, items)
        super().__setitem__(slice(None), field._read_paired_list(entity))
        return result

    def _belongs_to(self, field, entity):
        return self._field is field and self.entity is entity

    def append(self, entity):
        self._edit(list.append, entity)

    def extend(self, entities):
        self._edit(list.extend, entities)

    def remove(self, entity):
        self._edit(list.remove, entity)

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

    def __iadd__(self, entities):
        self._edit(list.__iadd__, entities)
        return self

    def __imul__(self, count):
        self._edit(list.__imul__, count)
        return self

    def reverse(self):
        self._edit(list.reverse)

    def sort(self, *, key=None, reverse=False):
        self._edit(list.sort, key=key, reverse=reverse)


class _ReverseList(_PairedList, RelationshipList):
    def __init__(self, items, field, entity):
        RelationshipList.__init__(self, entity, items, field.relation_type)
        self._field = field

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

    def __iadd__(self, entities):
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
        # EntityMeta reattaches inherited fields when defining subclasses.
        if not hasattr(self, "_declaring_owner"):
            self._declaring_owner = owner
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

        if annotation is ...:
            raise ValueError(f"{field_name} requires an entity_type or annotation")

        target, many = _annotation_parts(annotation)
        target = _annotation_entity_type(target)
        if target is None:
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


class _OwningRelationField(_RelationField):
    def __init__(self, *, back_relation, back_populates, **options):
        super().__init__(**options)
        if back_relation:
            if back_populates is not None:
                raise ValueError("Use either back_populates or back_relation")
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
        except (KeyError, ValueError) as error:
            target_name = getattr(self._entity_type, "__name__", self._entity_type)
            raise ValueError(
                f"{owner_name} cannot pair with "
                f"{target_name}.{self.back_populates}: {error.args[0]}"
            ) from error

        target_name = f"{target.__name__}.{self.back_populates}"
        pair_name = f"{owner_name} and {target_name}"
        relationship = getattr(target, self.back_populates, ...)
        if relationship is ...:
            raise ValueError(f"Cannot pair {pair_name}: {target_name} does not exist")
        if not isinstance(relationship, Relationship):
            raise ValueError(
                f"Cannot pair {pair_name}: {target_name} is not a Relationship"
            )
        if relationship._owning_field is not None:
            other = relationship._owning_field
            raise ValueError(
                f"Cannot pair {pair_name}: already paired with "
                f"{other._declaring_owner.__name__}.{other.name}"
            )
        try:
            related_type = relationship.entity_type
        except (KeyError, ValueError) as error:
            raise ValueError(f"Cannot pair {pair_name}: {error.args[0]}") from error
        if not issubclass(self._declaring_owner, related_type):
            raise ValueError(
                f"Cannot pair {pair_name}: "
                f"{target_name} refers to {related_type.__name__}"
            )

        relationship._owning_field = self
        self._relationship = relationship
        return relationship

    def _check_writable(self, owner):
        if not self.mode & AccessMode.SET:
            raise ValueError(f"Field '{self.name}' is read only")
        declaring_owner = self._declaring_owner
        if not isinstance(owner, declaring_owner) or (
            getattr(type(owner), self.name, None) is not self
        ):
            raise ValueError(
                f"Expected an owner of {declaring_owner.__name__}.{self.name}"
            )

    def _prepare_target(self, owner, target):
        self._check_target_relationship(target)
        if target.storage is not owner.storage:
            raise ValueError("Related entities must use the same storage")
        return target

    def _check_target_relationship(self, target):
        entity_type = self.entity_type
        if not isinstance(target, entity_type):
            raise ValueError(f"Expected {entity_type.__name__} for '{self.name}'")
        target_type = type(target)
        if getattr(target_type, self.back_populates, None) is not self._resolve_pair():
            raise ValueError(
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

    def _replace_paired_data(self, owner, data, *, loading=False):
        relationship = self._resolve_pair()
        if not loading:
            self._check_writable(owner)
        old_data = None if loading else owner._data.get(self.origin)
        old_sources = {self._source(item) for item in self._items(old_data)}
        sources = [self._source(item) for item in self._items(data)]
        new_sources = set(sources)
        if len(new_sources) != len(sources):
            raise ValueError(f"Duplicate entities for '{self.name}'")

        added = [source for source in sources if source not in old_sources]
        storage = owner.storage
        if not relationship.many:
            moves = []
            for source in added:
                old_owner = storage.get_one_related_entity(
                    source, self._declaring_owner, self
                )
                if old_owner is not None:
                    self._check_writable(old_owner)
                    moves.append((old_owner, source))
            for old_owner, source in moves:
                self._unlink(old_owner, source)

        for source in old_sources - new_sources:
            storage.remove_relation(source, owner, self)
        for source in added:
            storage.make_relation(source, owner, self)
        if not loading:
            owner._data[self.origin] = data

    def _unlink(self, owner, source):
        data = owner._data.get(self.origin)
        remaining = [item for item in self._items(data) if self._source(item) != source]
        self._replace_paired_data(owner, remaining if self.many else None)

    def _link(self, owner, item):
        if self.many:
            data = owner._data.get(self.origin) or []
            item = [*data, item]
        self._replace_paired_data(owner, item)

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
        back_relation: t.Any = False,
        mode: AccessMode = AccessMode.ALL,
        default: t.Any | t.Callable[[], t.Any] = ...,
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

    def load(self, data, instance: "Entity") -> t.NoReturn:
        data = super().load(data, instance)
        storage = instance.storage

        if self.many:
            items = (self.entity_type(data=item, storage=storage) for item in data)
            if self.back_populates is None:
                return NestedList(
                    entity=instance,
                    items=items,
                    relation_type=self.back_relation,
                )
            data = list(items)

        elif data is not None:
            data = self.entity_type(data=data, storage=storage)

            if self.back_relation:
                storage.make_relation(
                    from_=data,
                    to_=instance,
                    relation_type=self.back_relation,
                )

        if self.back_populates is not None:
            self._replace_paired_data(instance, data, loading=True)
        return data

    def __get__(self, instance: "Entity", owner):
        value = super().__get__(instance, owner)
        if instance and self.many and self.back_populates is not None:
            return _PairedList(value, self, instance)
        return value

    def _read_paired_list(self, instance):
        return instance._data.get(self.origin) or ()

    _write_paired_list = _OwningRelationField._set_paired_value

    def __set__(
        self,
        instance: "Entity",
        value: "list[Entity] | Entity",
    ):
        if not instance:
            return super().__set__(instance, value)

        if self.many and not isinstance(value, list):
            raise ValueError(
                "Only list accepted for nested field with many set to True, "
                f"got: {value}",
            )

        if self.back_populates is not None:
            self._set_paired_value(instance, value)
            return

        old_value = getattr(instance, self.origin)
        if self.many:
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
        self._owning_field = None

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
                entities = self._read_paired_list(instance)
            else:
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
            field._check_writable(owner)
            if owner.storage is not target.storage:
                raise ValueError("Related entities must use the same storage")
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
        related_entity_field: Field | t.Any,
        back_relation: t.Any = False,
        many: bool | None = None,
        mode: AccessMode = AccessMode.GET_SET_LOAD,
        default: t.Any | t.Callable[[], t.Any] = ...,
        origin: str | None = None,
        destination: str | None = None,
        key_manager: KeyManager | None = None,
        required: bool = True,
        *,
        back_populates: str | None = None,
    ):
        if not related_entity_field.pk:
            raise ValueError(
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
            raise ValueError(
                f"{target.__name__} does not use {key_field.name} as its key"
            )
        return target

    def _prepare_target(self, owner, target):
        super()._prepare_target(owner, target)
        data = self.key_manager.prepare_to_set(target)
        if data is None and not self.many:
            raise ValueError(f"Expected a non-null key for '{self.name}'")
        key = self.key_manager.get(data)
        if owner.storage.get(self.related_entity_field, key) is not target:
            raise ValueError(f"Expected a stored target for '{self.name}'")
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

        if self.back_populates is not None:
            for item in self._items(data):
                self._lookup_target(storage, self.key_manager.get(item))
            self._replace_paired_data(instance, data, loading=True)
            return data

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
            items = self._get_many(instance)
            if self.back_populates is not None:
                return _PairedList(items, self, instance)
            return items
        else:
            key = self.key_manager.get(data)
            entity = self._lookup_target(instance.storage, key)

            if not entity and self.required:
                raise ValueError(
                    f"Can't find {self.related_entity_field}={key} in storage",
                )

            return entity

    def _get_many(self, instance):
        result = []
        for item in instance._data.get(self.origin) or ():
            key = self.key_manager.get(item)
            entity = self._lookup_target(instance.storage, key)
            if entity:
                result.append(entity)
            elif self.required:
                raise ValueError(
                    f"Can't find {self.related_entity_field}={key} in storage",
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
        value: "Entity | list[Entity]",
    ):
        if not instance:
            return super().__set__(instance, value)

        if self.back_populates is not None:
            if isinstance(value, _PairedList) and value._belongs_to(self, instance):
                self._write_paired_list(instance, value)
            else:
                self._set_paired_value(instance, value)
            return

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
