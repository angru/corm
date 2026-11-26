import subprocess
import sys
from pathlib import Path


def test_entity_enumeration_experiment():
    subprocess.run(
        [sys.executable, "-m", "experiments.entity_enumeration"],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
    )
