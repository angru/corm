# Reassign a task with FastAPI

This endpoint accepts a task, its current and prospective owners, and the ID of
the new owner. It returns the edited task with the names of both owners. Each
request supplies its own data, so the endpoint also works as a preview without
a database.

From the repository root, start the example:

```sh
uv run --locked --group fastapi-example uvicorn --port 8765 --app-dir docs/recipes fastapi_app:app
```

Send a request in another terminal:

```sh
curl -sS http://127.0.0.1:8765/tasks/reassign \
  -H 'Content-Type: application/json' \
  -d '{"users":[{"id":1,"name":"Amina"},{"id":2,"name":"Lee"}],"task":{"title":"Invoice","ownerId":1,"internal":"private note"},"new_owner_id":2}'
```

```json
{"title":"Invoice","ownerId":2,"previous_owner":"Amina","owner_name":"Lee"}
```

## From HTTP fields to linked entities

Pydantic reads the JSON key `ownerId` into `TaskInput.owner_id`.
`model_dump(by_alias=True)` restores the wire name in the dictionary that
Corm wraps. The `KeyNested` field resolves that key to a `User` in the request's
`Storage`. Assigning a different user to `task.owner` writes the new ID back to
the dictionary. A subsequent request can reuse the same numeric IDs for other
users because it creates a fresh store.

Task input accepts extra keys such as `internal`. Corm preserves them during
the edit. FastAPI filters the exported dictionary through `TaskReply`, which
declares the public response fields. Invalid IDs, missing owners and duplicate
user IDs produce HTTP 422.

```python
--8<-- "docs/recipes/fastapi_app.py"
```

The `fastapi-example` dependency group provides the HTTP tools for this
recipe. Installing `corm` alone keeps the library's runtime dependencies empty.
To exercise the endpoint in process:

```sh
uv run --locked --group fastapi-example --group test pytest -q docs/recipes/test_fastapi_app.py
```
