import asyncio

from corm import Entity, Field, KeyNested, Storage


class User(Entity):
    id: int = Field(pk=True)
    name: str


class Ticket(Entity):
    owner: User = KeyNested(User.id, origin="owner_id")


async def process(name: str, storage: Storage, ready: asyncio.Barrier) -> str:
    user = User({"id": 7, "name": name}, storage)
    await ready.wait()  # Both documents have registered user 7.
    ticket = Ticket({"owner_id": 7}, storage)
    assert ticket.owner is user
    return ticket.owner.name


async def main() -> None:
    ready = asyncio.Barrier(2)
    names = await asyncio.gather(
        process("Amina", Storage(), ready),
        process("Lee", Storage(), ready),
    )
    assert names == ["Amina", "Lee"]


asyncio.run(main())
