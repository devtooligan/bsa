import unittest

class TestBasic(unittest.TestCase):
    def test_basic(self):
        """Basic test to verify that unittest is working."""
        self.assertEqual(1, 1)

if __name__ == '__main__':
    unittest.main()