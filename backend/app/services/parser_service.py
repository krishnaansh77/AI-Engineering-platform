"""Tree-sitter based code parser for Python, JavaScript, and TypeScript.

Extracts semantically meaningful code chunks (functions, classes, methods)
with rich metadata for embedding and retrieval.
"""
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Maximum lines in a single chunk before we split further
MAX_CHUNK_LINES = 150
# Minimum lines to bother creating a chunk (skip tiny stubs)
MIN_CHUNK_LINES = 3


@dataclass
class ParsedChunk:
    """A single semantically meaningful code chunk extracted from a source file."""

    chunk_type: str  # "function" | "class" | "method" | "module" | "other"
    symbol_name: Optional[str]
    parent_symbol: Optional[str]  # class name if this is a method
    start_line: int  # 1-indexed
    end_line: int  # 1-indexed, inclusive
    content: str
    docstring: Optional[str]
    imports: List[str]
    language: str


@lru_cache(maxsize=None)
def _get_python_parser():
    """Return a cached tree-sitter parser for Python."""
    try:
        import tree_sitter_python as tspython
        from tree_sitter import Language, Parser

        PY_LANGUAGE = Language(tspython.language())
        try:
            parser = Parser()
            parser.set_language(PY_LANGUAGE)
        except (TypeError, AttributeError):
            parser = Parser(PY_LANGUAGE)
        return parser
    except Exception as e:
        logger.warning("Could not load tree-sitter Python: %s", e)
        return None


@lru_cache(maxsize=None)
def _get_js_parser():
    """Return a cached tree-sitter parser for JavaScript."""
    try:
        import tree_sitter_javascript as tsjs
        from tree_sitter import Language, Parser

        JS_LANGUAGE = Language(tsjs.language())
        try:
            parser = Parser()
            parser.set_language(JS_LANGUAGE)
        except (TypeError, AttributeError):
            parser = Parser(JS_LANGUAGE)
        return parser
    except Exception as e:
        logger.warning("Could not load tree-sitter JavaScript: %s", e)
        return None


@lru_cache(maxsize=None)
def _get_ts_parser():
    """Return a cached tree-sitter parser for TypeScript."""
    try:
        import tree_sitter_typescript as tsts
        from tree_sitter import Language, Parser

        TS_LANGUAGE = Language(tsts.language_typescript())
        try:
            parser = Parser()
            parser.set_language(TS_LANGUAGE)
        except (TypeError, AttributeError):
            parser = Parser(TS_LANGUAGE)
        return parser
    except Exception as e:
        logger.warning("Could not load tree-sitter TypeScript: %s", e)
        return None


def _get_node_text(node, source_bytes: bytes) -> str:
    """Extract the text for a tree-sitter node."""
    return source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _extract_python_docstring(node, source_bytes: bytes) -> Optional[str]:
    """Extract docstring from a Python function or class body."""
    for child in node.children:
        if child.type == "block":
            for stmt in child.children:
                if stmt.type == "expression_statement":
                    for inner in stmt.children:
                        if inner.type == "string":
                            raw = _get_node_text(inner, source_bytes)
                            return raw.strip().strip('"""').strip("'''").strip('"').strip("'").strip()
    return None


def _split_large_chunk(chunk: ParsedChunk, max_lines: int = MAX_CHUNK_LINES) -> List[ParsedChunk]:
    """Split a chunk that's too large into smaller overlapping sub-chunks."""
    lines = chunk.content.split("\n")
    if len(lines) <= max_lines:
        return [chunk]

    sub_chunks = []
    overlap = 20  # lines of overlap between sub-chunks
    step = max_lines - overlap
    i = 0
    part = 1

    while i < len(lines):
        end = min(i + max_lines, len(lines))
        sub_content = "\n".join(lines[i:end])
        sub_name = f"{chunk.symbol_name}_part{part}" if chunk.symbol_name else f"part{part}"
        sub_chunks.append(
            ParsedChunk(
                chunk_type=chunk.chunk_type,
                symbol_name=sub_name,
                parent_symbol=chunk.parent_symbol,
                start_line=chunk.start_line + i,
                end_line=chunk.start_line + end - 1,
                content=sub_content,
                docstring=chunk.docstring if i == 0 else None,
                imports=chunk.imports,
                language=chunk.language,
            )
        )
        if end == len(lines):
            break
        i += step
        part += 1

    return sub_chunks


class ParserService:
    """Parse source files into structured code chunks using Tree-sitter."""

    def parse_file(self, file_path: str, language: str) -> List[ParsedChunk]:
        """Parse a source file and return a list of code chunks.

        Args:
            file_path: Absolute path to the source file
            language: One of "python", "javascript", "typescript"

        Returns:
            List of ParsedChunk objects ready for embedding
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()
        except OSError as e:
            logger.error("Failed to read file %s: %s", file_path, e)
            return []

        if not source.strip():
            return []

        try:
            if language == "python":
                return self._parse_python(source, language)
            elif language in ("javascript", "typescript"):
                return self._parse_js_ts(source, language)
            else:
                return self._fallback_chunk(source, language)
        except Exception as e:
            logger.error("Parser error for %s (%s): %s", file_path, language, e)
            return self._fallback_chunk(source, language)

    # ─── Python ───────────────────────────────────────────────────────────────

    def _parse_python(self, source: str, language: str) -> List[ParsedChunk]:
        """Parse Python source into chunks using tree-sitter."""
        parser = _get_python_parser()
        if parser is None:
            return self._fallback_chunk(source, language)

        source_bytes = source.encode("utf-8")
        tree = parser.parse(source_bytes)
        root = tree.root_node

        chunks: List[ParsedChunk] = []
        imports = self._extract_python_imports(root, source_bytes)

        # Module-level chunk: top-level imports
        if imports:
            import_lines = [
                l for l in source.split("\n")
                if l.startswith("import ") or l.startswith("from ")
            ]
            if import_lines:
                chunks.append(ParsedChunk(
                    chunk_type="module",
                    symbol_name="__imports__",
                    parent_symbol=None,
                    start_line=1,
                    end_line=len(import_lines),
                    content="\n".join(import_lines),
                    docstring=None,
                    imports=imports,
                    language=language,
                ))

        for node in root.children:
            if node.type == "class_definition":
                class_name = None
                for child in node.children:
                    if child.type == "identifier":
                        class_name = _get_node_text(child, source_bytes)
                        break
                class_doc = _extract_python_docstring(node, source_bytes)

                # Class-level chunk (header + docstring only)
                class_content = _get_node_text(node, source_bytes)
                chunks.append(ParsedChunk(
                    chunk_type="class",
                    symbol_name=class_name,
                    parent_symbol=None,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    content=class_content,
                    docstring=class_doc,
                    imports=imports,
                    language=language,
                ))

                # Extract methods
                for child in node.children:
                    if child.type == "block":
                        for stmt in child.children:
                            if stmt.type in ("function_definition", "decorated_definition"):
                                func_node = stmt
                                if stmt.type == "decorated_definition":
                                    for inner in stmt.children:
                                        if inner.type == "function_definition":
                                            func_node = inner
                                            break
                                method_chunks = self._extract_python_function(
                                    func_node, source_bytes, imports, language,
                                    parent_symbol=class_name
                                )
                                chunks.extend(method_chunks)

            elif node.type in ("function_definition", "decorated_definition"):
                func_node = node
                if node.type == "decorated_definition":
                    for child in node.children:
                        if child.type == "function_definition":
                            func_node = child
                            break
                func_chunks = self._extract_python_function(
                    func_node, source_bytes, imports, language, parent_symbol=None
                )
                chunks.extend(func_chunks)

        # Fall back to whole-file chunk if nothing was extracted
        if not chunks:
            return self._fallback_chunk(source, language)

        return chunks

    def _extract_python_function(
        self,
        node,
        source_bytes: bytes,
        imports: List[str],
        language: str,
        parent_symbol: Optional[str] = None,
    ) -> List[ParsedChunk]:
        """Extract a Python function/method as a chunk (or split if large)."""
        func_name = None
        for child in node.children:
            if child.type == "identifier":
                func_name = _get_node_text(child, source_bytes)
                break

        content = _get_node_text(node, source_bytes)
        doc = _extract_python_docstring(node, source_bytes)
        start = node.start_point[0] + 1
        end = node.end_point[0] + 1
        lines = end - start

        if lines < MIN_CHUNK_LINES:
            return []

        chunk = ParsedChunk(
            chunk_type="method" if parent_symbol else "function",
            symbol_name=func_name,
            parent_symbol=parent_symbol,
            start_line=start,
            end_line=end,
            content=content,
            docstring=doc,
            imports=imports,
            language=language,
        )
        return _split_large_chunk(chunk)

    def _extract_python_imports(self, root, source_bytes: bytes) -> List[str]:
        """Extract all top-level import strings from a Python file."""
        imports = []
        for node in root.children:
            if node.type in ("import_statement", "import_from_statement"):
                imports.append(_get_node_text(node, source_bytes).strip())
        return imports

    # ─── JavaScript / TypeScript ──────────────────────────────────────────────

    def _parse_js_ts(self, source: str, language: str) -> List[ParsedChunk]:
        """Parse JavaScript or TypeScript source into chunks using tree-sitter."""
        parser = _get_ts_parser() if language == "typescript" else _get_js_parser()
        if parser is None:
            return self._fallback_chunk(source, language)

        source_bytes = source.encode("utf-8")
        tree = parser.parse(source_bytes)
        root = tree.root_node

        chunks: List[ParsedChunk] = []
        imports = self._extract_js_imports(root, source_bytes)

        if imports:
            chunks.append(ParsedChunk(
                chunk_type="module",
                symbol_name="__imports__",
                parent_symbol=None,
                start_line=1,
                end_line=len(imports),
                content="\n".join(imports),
                docstring=None,
                imports=imports,
                language=language,
            ))

        self._walk_js_node(root, source_bytes, imports, language, chunks, parent_class=None)

        if not chunks:
            return self._fallback_chunk(source, language)

        return chunks

    def _walk_js_node(
        self,
        node,
        source_bytes: bytes,
        imports: List[str],
        language: str,
        chunks: List[ParsedChunk],
        parent_class: Optional[str],
    ) -> None:
        """Recursively walk a JS/TS AST node and extract functions/classes."""
        for child in node.children:
            if child.type in (
                "function_declaration",
                "function",
                "arrow_function",
                "generator_function_declaration",
            ):
                name = None
                for c in child.children:
                    if c.type == "identifier":
                        name = _get_node_text(c, source_bytes)
                        break
                content = _get_node_text(child, source_bytes)
                start = child.start_point[0] + 1
                end = child.end_point[0] + 1
                if (end - start) >= MIN_CHUNK_LINES:
                    chunk = ParsedChunk(
                        chunk_type="method" if parent_class else "function",
                        symbol_name=name,
                        parent_symbol=parent_class,
                        start_line=start,
                        end_line=end,
                        content=content,
                        docstring=None,
                        imports=imports,
                        language=language,
                    )
                    chunks.extend(_split_large_chunk(chunk))

            elif child.type == "lexical_declaration":
                # const foo = () => { ... }
                for decl in child.children:
                    if decl.type == "variable_declarator":
                        name = None
                        func_node = None
                        for c in decl.children:
                            if c.type == "identifier":
                                name = _get_node_text(c, source_bytes)
                            elif c.type in ("arrow_function", "function"):
                                func_node = c
                        if func_node:
                            content = _get_node_text(child, source_bytes)
                            start = child.start_point[0] + 1
                            end = child.end_point[0] + 1
                            if (end - start) >= MIN_CHUNK_LINES:
                                chunk = ParsedChunk(
                                    chunk_type="function",
                                    symbol_name=name,
                                    parent_symbol=parent_class,
                                    start_line=start,
                                    end_line=end,
                                    content=content,
                                    docstring=None,
                                    imports=imports,
                                    language=language,
                                )
                                chunks.extend(_split_large_chunk(chunk))

            elif child.type == "class_declaration":
                name = None
                for c in child.children:
                    if c.type == "identifier":
                        name = _get_node_text(c, source_bytes)
                        break
                content = _get_node_text(child, source_bytes)
                start = child.start_point[0] + 1
                end = child.end_point[0] + 1
                chunks.append(ParsedChunk(
                    chunk_type="class",
                    symbol_name=name,
                    parent_symbol=None,
                    start_line=start,
                    end_line=end,
                    content=content,
                    docstring=None,
                    imports=imports,
                    language=language,
                ))
                # Recurse into class body for methods
                self._walk_js_node(child, source_bytes, imports, language, chunks, parent_class=name)

            elif child.type == "method_definition":
                name = None
                for c in child.children:
                    if c.type == "property_identifier":
                        name = _get_node_text(c, source_bytes)
                        break
                content = _get_node_text(child, source_bytes)
                start = child.start_point[0] + 1
                end = child.end_point[0] + 1
                if (end - start) >= MIN_CHUNK_LINES:
                    chunk = ParsedChunk(
                        chunk_type="method",
                        symbol_name=name,
                        parent_symbol=parent_class,
                        start_line=start,
                        end_line=end,
                        content=content,
                        docstring=None,
                        imports=imports,
                        language=language,
                    )
                    chunks.extend(_split_large_chunk(chunk))

            else:
                # Recurse into other node types (export statements, etc.)
                self._walk_js_node(child, source_bytes, imports, language, chunks, parent_class)

    def _extract_js_imports(self, root, source_bytes: bytes) -> List[str]:
        """Extract import/require statements from a JS/TS file."""
        imports = []
        for node in root.children:
            if node.type == "import_statement":
                imports.append(_get_node_text(node, source_bytes).strip())
            elif node.type in ("lexical_declaration", "variable_declaration"):
                text = _get_node_text(node, source_bytes)
                if "require(" in text:
                    imports.append(text.strip())
        return imports

    # ─── Fallback ─────────────────────────────────────────────────────────────

    def _fallback_chunk(self, source: str, language: str) -> List[ParsedChunk]:
        """Create a single whole-file chunk when AST parsing fails or yields nothing."""
        lines = source.split("\n")
        return [
            ParsedChunk(
                chunk_type="module",
                symbol_name="__file__",
                parent_symbol=None,
                start_line=1,
                end_line=len(lines),
                content=source[:8000],  # Cap at 8k chars for embedding
                docstring=None,
                imports=[],
                language=language,
            )
        ]
