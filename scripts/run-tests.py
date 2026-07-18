from __future__ import annotations

import sys
import unittest
from pathlib import Path


def run() -> int:
    repository_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repository_root / "src"))
    suite = unittest.defaultTestLoader.discover(
        str(repository_root / "tests"),
        top_level_dir=str(repository_root),
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(run())
