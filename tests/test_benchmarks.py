import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_benchmark(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "benchmarks.dict_vs_corm", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_dict_vs_corm_runs_each_workload():
    result = run_benchmark("--repeat", "2", "1", "17")

    assert result.returncode == 0, result.stderr
    assert "1 tasks, median of 2 samples" in result.stdout
    assert "17 tasks, median of 2 samples" in result.stdout
    for label in ("Setup", "Nested tasks", "Task to assignee", "Assignee to tasks"):
        assert result.stdout.count(label) == 2


@pytest.mark.parametrize("args", [("0",), ("--repeat", "-1")])
def test_dict_vs_corm_rejects_nonpositive_inputs(args):
    result = run_benchmark(*args)

    assert result.returncode == 2
    assert "must be a positive integer" in result.stderr
