import typing as t

import itertools
from collections import defaultdict

from corm import constants

if t.TYPE_CHECKING:
    from corm.model import Model, Field


class Storage:
    _id_sequence = itertools.count(-1, -1)

    def __init__(self):
        self._entities: t.Dict[t.Tuple['Field', t.Any], 'Model'] = {}
        self._relations = defaultdict(list)

    def add(self, entity: 'Model'):
        if entity.__pk_fields__:
            for field in entity.__pk_fields__:
                value = getattr(entity, field.name)
                self._entities[field, value] = entity

    def get(self, field, entity_key) -> 'Model':
        return self._entities.get((field, entity_key))

    def make_relation(self, from_: 'Model', relation_type: constants.RelationType, to_: 'Model'):
        # TODO: probably weakref will be better
        relations = self._relations[from_, relation_type, type(to_)]

        if to_ not in relations:
            relations.append(to_)

    def get_related_entities(
            self, entity: 'Model', entity_type: t.Type['Model'], relation_type: constants.RelationType,
    ) -> t.List['Model']:
        return self._relations[entity, relation_type, entity_type]

    def get_one_related_entity(
            self, entity: 'Model', entity_type: t.Type['Model'], relation_type: constants.RelationType,
    ) -> t.Optional['Model']:
        entities = self._relations[entity, relation_type, entity_type]

        if entities:
            return entities[0]
