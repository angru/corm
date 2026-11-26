import asyncio

import httpx
from fastapi_app import app


def test_reassignment():
    async def check():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            body = {
                "users": [{"id": 1, "name": "Amina"}, {"id": 2, "name": "Lee"}],
                "task": {"title": "Invoice", "ownerId": 1, "internal": "private note"},
                "new_owner_id": 2,
            }
            for name in ("Lee", "Sam"):
                body["users"][1]["name"] = name
                result = await client.post("/tasks/reassign", json=body)
                assert result.status_code == 200
                assert result.json() == {
                    "title": "Invoice",
                    "ownerId": 2,
                    "previous_owner": "Amina",
                    "owner_name": name,
                }

            for changes in (
                {"new_owner_id": "invalid"},
                {"new_owner_id": 3},
                {"task": {"title": "Invoice", "ownerId": 9}},
                {"users": [body["users"][0], body["users"][0]]},
            ):
                result = await client.post("/tasks/reassign", json=body | changes)
                assert result.status_code == 422

    asyncio.run(check())
