from copy import deepcopy

from corm import Entity, Field, KeyNested, Nested, Relationship, Storage


class User(Entity):
    id: int = Field(pk=True)
    tickets: list["Ticket"] = Relationship()


class Ticket(Entity):
    owner: User = KeyNested(User.id, origin="owner_id", back_populates="tickets")
    labels: list[str]


class Board(Entity):
    users: list[User] = Nested()
    tickets: list[Ticket] = Nested()


source = Storage()
board = Board(
    {"users": [{"id": 7}], "tickets": [{"owner_id": 7, "labels": ["billing"]}]},
    source,
)
destination = Storage()
copied = Board(deepcopy(board.dict()), destination)

user, ticket = board.users[0], board.tickets[0]
new_user, new_ticket = copied.users[0], copied.tickets[0]
assert copied.dict() == board.dict()
assert source.get(User.id, 7) is user
assert destination.get(User.id, 7) is new_user
assert new_user is not user and new_ticket is not ticket
assert ticket.owner is user and user.tickets == [ticket]
assert new_ticket.owner is new_user and new_user.tickets == [new_ticket]

new_ticket.labels.append("reviewed")
assert ticket.labels == ["billing"]
assert new_ticket.labels == ["billing", "reviewed"]
