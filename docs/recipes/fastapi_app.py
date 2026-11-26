from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict
from pydantic import Field as WireField

from corm import (
    DuplicateKeyError,
    Entity,
    EntityNotFoundError,
    Field,
    KeyNested,
    Storage,
)


class User(Entity):
    id: int = Field(pk=True)
    name: str


class Task(Entity):
    title: str
    owner: User = KeyNested(User.id, origin="ownerId")


class UserInput(BaseModel):
    id: int
    name: str


class TaskInput(BaseModel):
    model_config = ConfigDict(extra="allow")
    title: str
    owner_id: int = WireField(alias="ownerId")


class Reassignment(BaseModel):
    users: list[UserInput]
    task: TaskInput
    new_owner_id: int


class TaskReply(BaseModel):
    title: str
    owner_id: int = WireField(alias="ownerId")
    previous_owner: str
    owner_name: str


app = FastAPI()


@app.post("/tasks/reassign", response_model=TaskReply)
def reassign(body: Reassignment):
    storage = Storage()
    try:
        for member in body.users:
            User(member.model_dump(), storage)
        task = Task(body.task.model_dump(by_alias=True), storage)
        previous_owner = task.owner.name
    except (DuplicateKeyError, EntityNotFoundError) as exc:
        raise HTTPException(
            422, "User IDs must be unique and include the task owner"
        ) from exc

    new_owner = storage.get(User.id, body.new_owner_id)
    if not isinstance(new_owner, User):
        raise HTTPException(422, "Unknown new owner")
    task.owner = new_owner
    return {
        **task.dict(),
        "previous_owner": previous_owner,
        "owner_name": task.owner.name,
    }
