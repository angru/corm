import functools
import typing as t

from collections import defaultdict

from corm import constants

if t.TYPE_CHECKING:
    from corm.entity import Entity, Field


class Storage:
    def __init__(self):
        self._entities: t.Dict[t.Tuple['Field', t.Any], 'Entity'] = {}
        self._relations = defaultdict(functools.partial(defaultdict, list))
        self._key_relations = defaultdict(functools.partial(defaultdict, list))

    def add(self, entity: 'Entity'):
        if entity.__pk_fields__:
            for field in entity.__pk_fields__:
                value = getattr(entity, field.name)
                key = (field, value)

                if key in self._entities:
                    raise ValueError(f'{field}={value} already in storage')

                self._entities[key] = entity

    def get(self, field, entity_key) -> 'Entity':
        return self._entities.get((field, entity_key))

    def make_key_relation(
            self, field_from: 'Field', key_from: t.Any, relation_type: constants.RelationType, to: 'Entity',
    ):
        relations = self._key_relations[field_from, key_from, relation_type][type(to)]

        if to not in relations:
            relations.append(to)
        else:
            raise ValueError(f'Relation type {relation_type} already exists between {field_from}={key_from} and {to}')

    def get_key_relations(
            self, field_from, key_from, relation_type: constants.RelationType, to: t.Type['Entity'],
    ):
        return self._key_relations[field_from, key_from, relation_type][to]

    def get_one_key_related_entity(self, field_from, key_from, relation_type: constants.RelationType, to: t.Type[
        'Entity']):
        relations = self._key_relations[field_from, key_from, relation_type][to]

        if relations:
            return relations[0]

    def make_relation(self, from_: 'Entity', to_: 'Entity', relation_type: constants.RelationType):
        # TODO: probably weakref will be better
        relations = self._relations[from_][type(to_), relation_type]

        if to_ not in relations:
            relations.append(to_)
        else:
            raise ValueError(f'Relation type {relation_type} already exists between {from_} and {to_}')

    def get_related_entities(
            self, entity: 'Entity', entity_type: t.Type['Entity'], relation_type: constants.RelationType,
    ) -> t.List['Entity']:
        return self._relations[entity][entity_type, relation_type]

    def get_one_related_entity(
            self, entity: 'Entity', entity_type: t.Type['Entity'], relation_type: constants.RelationType,
    ) -> t.Optional['Entity']:
        entities = self._relations[entity][entity_type, relation_type]

        if entities:
            return entities[0]

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
