import subprocess
import sys
from pathlib import Path


def test_document_rekey_preserves_identity_and_rejects_conflicts():
    subprocess.run(
        [sys.executable, "-m", "experiments.document_rekey"],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
    )


def test_late_manager_failure_discards_prepared_records(monkeypatch):
    from copy import deepcopy

    import pytest

    from experiments.document_rekey import Directory, Group, Storage, User, rekey

    store = Storage()
    directory = Directory(
        {
            "users": [{"id": 1}],
            "lead_id": 1,
            "groups": [
                {"members": [{"user_id": 1, "rank": rank, "metadata": {"tags": []}}]}
                for rank in (1, 2)
            ],
        },
        store,
    )
    user = directory.lead
    before = deepcopy(directory.dict())
    calls = []

    def rewrite(record, new_id):
        record["metadata"]["tags"].append("modified")
        calls.append(record["rank"])
        if record["rank"] == 2:
            raise RuntimeError("Rejected last membership")
        record["user_id"] = new_id
        return record

    monkeypatch.setattr(Group.members.key_manager, "rewrite_key", rewrite)
    with pytest.raises(RuntimeError, match="Rejected last membership"):
        rekey(directory, user, 5)
    assert calls == [1, 2]
    assert directory.dict() == before
    assert store.get(User.id, 1) is directory.lead is user
    assert store.get(User.id, 5) is None
    assert user.groups == directory.groups
    assert all(group.members == [user] for group in directory.groups)
