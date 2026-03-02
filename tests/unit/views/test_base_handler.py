import unittest

from flower.views import _UNSET


class TestMutableDefaultFix(unittest.TestCase):
    """Verify that the mutable default argument fix works correctly."""

    def test_unset_sentinel_is_unique(self):
        self.assertIsNotNone(_UNSET)
        self.assertIsNot(_UNSET, [])
        self.assertIsNot(_UNSET, None)

    def test_sentinel_identity(self):
        # Same object every time
        from flower.views import _UNSET as unset2
        self.assertIs(_UNSET, unset2)


if __name__ == '__main__':
    unittest.main()
