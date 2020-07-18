import collections
import functools
import typing as t

from collections import defaultdict

if t.TYPE_CHECKING:
    from corm.entity import Entity, Field

EntityRef = collections.namedtuple('EntityRef', ['field', 'key'])


class Storage:
    def __init__(self):
        self._entities: t.Dict[t.Tuple['Field', t.Any], 'Entity'] = {}
        self._relations = defaultdict(functools.partial(defaultdict, list))

    def add(self, entity: 'Entity'):
        if entity.__pk_fields__:
            for field in entity.__pk_fields__:
                value = getattr(entity, field.name)
                key = EntityRef(field, value)

                if key in self._entities:
                    raise ValueError(f'{field}={value} already in storage')

                # resolve reference relations
                relations = self._relations.pop(key, None)

                if relations:
                    self._relations[entity] = relations

                self._entities[key] = entity

    def get(self, field, entity_key) -> 'Entity':
        return self._entities.get(EntityRef(field, entity_key))

    def make_key_relation(
        self,
        field_from: 'Field',
        key_from: t.Any,
        relation_type: t.Any,
        to: 'Entity',
    ):
        entity = self.get(field_from, key_from)

        if entity is None:
            # if entity with that key is not present in storage yet
            # we resolve it later
            entity = EntityRef(field=field_from, key=key_from)

        self.make_relation(from_=entity, to_=to, relation_type=relation_type)

    def make_relation(
        self,
        from_: t.Union['Entity', 'EntityRef'],
        to_: t.Union['Entity', 'EntityRef'],
        relation_type: t.Any,
    ):
        # TODO: probably weakref will be better
        relations = self._relations[from_][type(to_), relation_type]

        if to_ not in relations:
            relations.append(to_)
        else:
            raise ValueError(
                f'Relation type {relation_type} already exists '
                f'between {from_} and {to_}',
            )

    def get_related_entities(
        self,
        entity: ['Entity', 'EntityRef'],
        related_entity_type: t.Type['Entity'],
        relation_type: t.Any,
    ) -> t.List['Entity']:
        return self._relations[entity][related_entity_type, relation_type]

    def get_one_related_entity(
        self,
        entity: t.Union['Entity', 'EntityRef'],
        related_entity_type: t.Type['Entity'],
        relation_type: t.Any,
    ) -> t.Optional['Entity']:
        entities = self._relations[entity][related_entity_type, relation_type]

        if entities:
            return entities[0]

    def remove_relation(
        self,
        from_: t.Union['Entity', 'EntityRef'],
        to_: t.Union['Entity', 'EntityRef'],
        relation_type: t.Any,
    ) -> t.NoReturn:
        self._relations[from_][type(to_), relation_type].remove(to_)

    def remove_relations(
        self,
        entity: t.Union['Entity', 'EntityRef'],
        related_entity_type: t.Type['Entity'],
        relation_type: t.Any,
    ) -> t.NoReturn:
        self._relations[entity][related_entity_type, relation_type].clear()

    def merge(self, entity: 'Entity'):
        raise NotImplementedError

    def select(self, entity_type: t.Type['Entity']) -> 'Query':
        raise NotImplementedError


class Query:
    def filter(self, *args, **kwargs) -> 'Query':
        raise NotImplementedError

    def first(self) -> 'Entity':
        raise NotImplementedError

    def one(self) -> 'Entity':
        raise NotImplementedError

    def all(self) -> t.List['Entity']:
        raise NotImplementedError
