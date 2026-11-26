import unittest

from camera_monitor.updates import version_tuple


class VersionTupleTests(unittest.TestCase):
    def test_tags_compare_numerically(self):
        self.assertGreater(version_tuple('v0.10.0'), version_tuple('0.9.1'))
        self.assertEqual(version_tuple('v1.2.3'), (1, 2, 3))
        self.assertEqual(version_tuple(''), (0,))
        self.assertEqual(version_tuple('v1.2.3-beta'), (1, 2, 3))


if __name__ == '__main__':
    unittest.main()
