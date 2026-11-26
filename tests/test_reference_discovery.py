from corm import Entity, Field, KeyManager, KeyNested, Nested, Relationship, Storage
from experiments.reference_discovery import Reference, unpaired_references


def test_discover_stored_occurrences_inside_one_document():
    class User(Entity):
        id: int = Field(pk=True)
        owners: list["Node"] = Relationship()

    class Team(Entity):
        id: int = Field(pk=True)

    class MemberKey(KeyManager):
        def get(self, record):
            return record["user"]

    class Node(Entity):
        children: list["Node"] = Nested(default=list)
        lead = KeyNested(User.id, origin="lead_id", default=None)
        members = KeyNested(User.id, many=True, key_manager=MemberKey(), default=list)
        team = KeyNested(Team.id, default=None)
        paired: User | None = KeyNested(User.id, back_populates="owners", default=None)

    store = Storage()
    user = User({"id": 1}, store)
    raw = [{"user": 1, "rank": 3}, {"user": 9}, {"user": 1, "rank": 2}]
    root = Node({"lead_id": 1, "children": [{"members": raw, "team": 1}]}, store)
    child = root.children[0]
    outside = Node({"lead_id": 1, "paired": 1}, store)
    foreign = Node({"lead_id": 1}, Storage())
    root.children = [child, child, foreign]
    child.children = [root]

    assert list(unpaired_references(root, User.id, 1)) == [
        Reference(root, Node.lead, None),
        Reference(child, Node.members, 0),
        Reference(child, Node.members, 2),
    ]
    assert list(unpaired_references(root, User.id, 9)) == [
        Reference(child, Node.members, 1)
    ]
    assert list(unpaired_references(outside, User.id, 1)) == [
        Reference(outside, Node.lead, None)
    ]
    assert root.lead is user
    assert user.owners == [outside]
    assert raw == [{"user": 1, "rank": 3}, {"user": 9}, {"user": 1, "rank": 2}]
