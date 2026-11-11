from corm import Entity, Field, KeyNested, Nested, Relationship, Storage


class User(Entity):
    id: int = Field(pk=True)
    name: str
    tasks: list["Task"] = Relationship()


class Task(Entity):
    title: str
    assignee: User = KeyNested(User.id, origin="assignee_id", back_populates="tasks")
    sprint: "Sprint | None" = Relationship()


class Sprint(Entity):
    name: str
    tasks: list[Task] = Nested(back_populates="sprint")


class Project(Entity):
    name: str
    users: list[User] = Nested()
    sprints: list[Sprint] = Nested()


payload = {
    "name": "Customer portal",
    "archived": False,
    "users": [{"id": 42, "name": "Amina", "timezone": "UTC"}],
    "sprints": [
        {
            "name": "Sprint 12",
            "tasks": [
                {
                    "title": "Add invoice download",
                    "assignee_id": 42,
                    "labels": ["billing"],
                }
            ],
        },
        {"name": "Sprint 13", "tasks": []},
    ],
}

project = Project(payload, Storage())
current_sprint, next_sprint = project.sprints
(task,) = current_sprint.tasks
(user,) = project.users

assert project.name == "Customer portal"
assert task.title == "Add invoice download"
assert task.sprint is current_sprint
assert task.assignee is user
assert user.tasks == [task]

task.sprint = next_sprint

assert current_sprint.tasks == []
assert next_sprint.tasks == [task]
assert task.sprint is next_sprint
assert task.assignee is user
assert user.tasks == [task]

assert project.dict() == {
    "name": "Customer portal",
    "archived": False,
    "users": [{"id": 42, "name": "Amina", "timezone": "UTC"}],
    "sprints": [
        {"name": "Sprint 12", "tasks": []},
        {
            "name": "Sprint 13",
            "tasks": [
                {
                    "title": "Add invoice download",
                    "assignee_id": 42,
                    "labels": ["billing"],
                }
            ],
        },
    ],
}
