import unittest
import tornado.testing

from glob import glob


def all():
    test_modules = list(map(lambda x: x.rstrip('.py').replace('/', '.'),
                            glob('tests/unit/*.py') + glob('tests/unit/**/*.py')))
    return unittest.defaultTestLoader.loadTestsFromNames(test_modules)


if __name__ == "__main__":
    tornado.testing.main()
