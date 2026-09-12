import unittest
from pathlib import Path

import tornado.testing


def all():
    test_dir = Path(__file__).resolve().parent
    return unittest.defaultTestLoader.discover(
        start_dir=str(test_dir),
        pattern='test_*.py',
        top_level_dir=str(test_dir.parents[1]),
    )


if __name__ == "__main__":
    tornado.testing.main()
