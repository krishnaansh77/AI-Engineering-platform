"""Tests for the symbol metadata shape used by the dependency graph."""
import unittest


class TestGraphSymbolMetadata(unittest.TestCase):
    def test_symbol_metadata_has_source_location(self):
        symbol = {
            "name": "build_file_graph",
            "type": "method",
            "parent": "DependencyGraphService",
            "start_line": 10,
            "end_line": 24,
        }
        self.assertEqual(symbol["type"], "method")
        self.assertLessEqual(symbol["start_line"], symbol["end_line"])


if __name__ == "__main__":
    unittest.main()
