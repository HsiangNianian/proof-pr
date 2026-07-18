from __future__ import annotations

import sys
from pathlib import Path


def run() -> int:
    repository_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repository_root / "src"))

    from proof_pr.cli import main

    return main()


if __name__ == "__main__":
    raise SystemExit(run())
