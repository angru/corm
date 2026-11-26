import subprocess
import sys
from pathlib import Path


def test_identifying_key_projection_experiment():
    subprocess.run(
        [sys.executable, "-m", "experiments.identifying_key_projection"],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
    )
