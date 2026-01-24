import unittest

class SimpleImportTest(unittest.TestCase):
    def test_import(self):
        try:
            import studio.pm
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import studio.pm: {e}")

if __name__ == '__main__':
    unittest.main()
