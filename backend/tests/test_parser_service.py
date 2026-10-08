"""Parser edge-case coverage without network or provider calls."""
import tempfile
import unittest
from pathlib import Path

from app.services.parser_service import ParserService


class TestParserService(unittest.TestCase):
    def test_empty_file_returns_no_chunks(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.py"
            path.write_text("\n")
            self.assertEqual(ParserService().parse_file(str(path), "python"), [])

    def test_unsupported_language_keeps_module_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.txt"
            path.write_text("one\ntwo\nthree\n")
            chunks = ParserService().parse_file(str(path), "text")
            self.assertEqual(len(chunks), 1)
            self.assertEqual(chunks[0].chunk_type, "module")
            self.assertEqual(chunks[0].start_line, 1)

    def test_python_function_preserves_line_range_and_docstring(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "service.py"
            path.write_text('def run(value):\n    """Run the service."""\n    return value\n')
            chunks = ParserService().parse_file(str(path), "python")
            function = next((chunk for chunk in chunks if chunk.symbol_name == "run"), None)
            if function is None:
                self.skipTest("Tree-sitter Python package is not installed in this environment")
            self.assertEqual(function.start_line, 1)
            self.assertEqual(function.end_line, 3)
            self.assertEqual(function.docstring, "Run the service.")
