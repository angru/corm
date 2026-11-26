import subprocess
import sys
from pathlib import Path


def test_document_rekey_preserves_identity_and_rejects_conflicts():
    subprocess.run(
        [sys.executable, "-m", "experiments.document_rekey"],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
    )
