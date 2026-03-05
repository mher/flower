import unittest

from flower.views import _UNSET


class TestUnsetSentinel(unittest.TestCase):
    def test_unset_is_unique_identity(self):
        """_UNSET must be a distinct singleton — not equal to common defaults."""
        self.assertIsNot(_UNSET, None)
        self.assertIsNot(_UNSET, [])
        self.assertIsNot(_UNSET, '')

    def test_unset_is_same_object(self):
        """Re-importing must yield the same object (module-level singleton)."""
        from flower.views import _UNSET as again
        self.assertIs(_UNSET, again)


if __name__ == '__main__':
    unittest.main()
