"""Build structural dependency graphs from indexed source-file imports."""
from pathlib import PurePosixPath
import posixpath
from typing import Dict, List, Set, Tuple
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

class DependencyGraphService:
    """Resolve indexed import statements into repository-local file edges."""

    async def build_file_graph(
        self, repo_id: uuid.UUID, db: AsyncSession
    ) -> dict:
        from app.models.code_chunk import CodeChunk
        from app.models.source_file import SourceFile

        files_result = await db.execute(
            select(SourceFile).where(SourceFile.repository_id == repo_id)
        )
        file_paths = sorted({f.file_path for f in files_result.scalars().all()})
        known_paths = set(file_paths)

        chunks_result = await db.execute(
            select(CodeChunk).where(CodeChunk.repository_id == repo_id)
        )

        edges: Set[Tuple[str, str, str]] = set()
        symbols_by_file: Dict[str, List[dict]] = {path: [] for path in file_paths}
        for chunk in chunks_result.scalars().all():
            source = chunk.file_path
            if chunk.symbol_name:
                symbols_by_file.setdefault(source, []).append(
                    {
                        "name": chunk.symbol_name,
                        "type": chunk.chunk_type,
                        "parent": chunk.parent_symbol,
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                    }
                )
            for raw_import in chunk.imports or []:
                target = self.resolve_import(source, raw_import, known_paths)
                if target and target != source:
                    edges.add((source, target, raw_import))

        nodes = [
            {
                "id": path,
                "file_path": path,
                "symbols": sorted(
                    symbols_by_file.get(path, []),
                    key=lambda symbol: (symbol["start_line"], symbol["name"]),
                ),
            }
            for path in file_paths
        ]
        edge_list = [
            {"source": source, "target": target, "import": import_text}
            for source, target, import_text in sorted(edges)
        ]
        return {
            "nodes": nodes,
            "edges": edge_list,
            "node_count": len(nodes),
            "edge_count": len(edge_list),
        }

    async def build_architecture_summary(
        self, repo_id: uuid.UUID, db: AsyncSession
    ) -> dict:
        """Summarize inferred repository layers and cross-layer dependencies."""
        graph = await self.build_file_graph(repo_id, db)
        layer_files: Dict[str, List[str]] = {}
        file_layers: Dict[str, str] = {}
        for node in graph["nodes"]:
            layer = self.classify_layer(node["file_path"])
            file_layers[node["id"]] = layer
            layer_files.setdefault(layer, []).append(node["file_path"])

        cross_layer_edges: Dict[Tuple[str, str], int] = {}
        for edge in graph["edges"]:
            source_layer = file_layers[edge["source"]]
            target_layer = file_layers[edge["target"]]
            if source_layer != target_layer:
                key = (source_layer, target_layer)
                cross_layer_edges[key] = cross_layer_edges.get(key, 0) + 1

        layers = [
            {
                "name": name,
                "file_count": len(paths),
                "files": sorted(paths)[:8],
            }
            for name, paths in sorted(layer_files.items(), key=lambda item: (-len(item[1]), item[0]))
        ]
        links = [
            {"source": source, "target": target, "edge_count": count}
            for (source, target), count in sorted(cross_layer_edges.items())
        ]
        return {"layers": layers, "cross_layer_links": links}

    async def build_test_summary(self, repo_id: uuid.UUID, db: AsyncSession) -> dict:
        """Build a conservative test-to-source relationship summary.

        This is a relationship heuristic, not a replacement for runtime coverage.
        """
        graph = await self.build_file_graph(repo_id, db)
        paths = [node["file_path"] for node in graph["nodes"]]
        test_files = {path for path in paths if self.classify_layer(path) == "tests"}
        source_files = set(paths) - test_files
        tested_files: Set[str] = set()

        for edge in graph["edges"]:
            if edge["source"] in test_files and edge["target"] in source_files:
                tested_files.add(edge["target"])

        # Match conventional names such as test_graph_service.py to
        # graph_service.py when an explicit import was not resolved.
        source_by_stem = {
            PurePosixPath(path).stem.lower(): path for path in source_files
        }
        for test_path in test_files:
            stem = PurePosixPath(test_path).stem.lower()
            candidates = [stem.removeprefix("test_"), stem.removesuffix("_test")]
            for candidate in candidates:
                if candidate in source_by_stem:
                    tested_files.add(source_by_stem[candidate])

        untested_files = sorted(source_files - tested_files)
        return {
            "test_file_count": len(test_files),
            "source_file_count": len(source_files),
            "tested_file_count": len(tested_files),
            "untested_file_count": len(untested_files),
            "tested_files": sorted(tested_files),
            "untested_files": untested_files,
        }

    async def build_repository_tour(self, repo_id: uuid.UUID, db: AsyncSession) -> dict:
        """Return a compact onboarding-oriented view of the repository structure."""
        graph = await self.build_file_graph(repo_id, db)
        connection_counts: Dict[str, int] = {node["id"]: 0 for node in graph["nodes"]}
        for edge in graph["edges"]:
            connection_counts[edge["source"]] += 1
            connection_counts[edge["target"]] += 1

        key_files = []
        for node in sorted(
            graph["nodes"],
            key=lambda item: (-connection_counts[item["id"]], item["file_path"]),
        )[:8]:
            key_files.append(
                {
                    "file_path": node["file_path"],
                    "connections": connection_counts[node["id"]],
                    "symbols": [symbol["name"] for symbol in node.get("symbols", [])[:6]],
                    "layer": self.classify_layer(node["file_path"]),
                }
            )
        return {
            "file_count": graph["node_count"],
            "relationship_count": graph["edge_count"],
            "key_files": key_files,
        }

    async def build_debt_summary(self, repo_id: uuid.UUID, db: AsyncSession) -> dict:
        """Return explainable structural debt signals, not a subjective quality score."""
        from app.models.code_chunk import CodeChunk

        graph = await self.build_file_graph(repo_id, db)
        chunk_result = await db.execute(select(CodeChunk).where(CodeChunk.repository_id == repo_id))
        chunks = list(chunk_result.scalars().all())
        connection_counts: Dict[str, int] = {node["id"]: 0 for node in graph["nodes"]}
        for edge in graph["edges"]:
            connection_counts[edge["source"]] += 1
            connection_counts[edge["target"]] += 1

        max_chunk_lines: Dict[str, int] = {}
        for chunk in chunks:
            size = max(0, chunk.end_line - chunk.start_line + 1)
            max_chunk_lines[chunk.file_path] = max(max_chunk_lines.get(chunk.file_path, 0), size)

        hotspots = []
        for path, count in sorted(connection_counts.items(), key=lambda item: -item[1])[:5]:
            if count > 0:
                hotspots.append({"file_path": path, "signal": "high connectivity", "value": count, "unit": "links"})
        for path, lines in sorted(max_chunk_lines.items(), key=lambda item: -item[1])[:5]:
            if lines >= 80:
                hotspots.append({"file_path": path, "signal": "large code chunk", "value": lines, "unit": "lines"})

        unique_hotspots = {}
        for hotspot in hotspots:
            unique_hotspots[(hotspot["file_path"], hotspot["signal"])] = hotspot
        return {
            "signals": sorted(unique_hotspots.values(), key=lambda item: (-item["value"], item["file_path"])),
            "files_analyzed": len(graph["nodes"]),
            "chunks_analyzed": len(chunks),
        }

    @staticmethod
    def classify_layer(file_path: str) -> str:
        """Infer a useful architecture layer from a repository-relative path."""
        normalized = file_path.lower().replace("\\", "/")
        parts = set(normalized.split("/"))
        name = normalized.rsplit("/", 1)[-1]
        if "test" in name or "tests" in parts or "__tests__" in parts:
            return "tests"
        if "frontend" in parts or normalized.startswith("src/"):
            return "frontend"
        if "backend" in parts or "api" in parts or "services" in parts:
            return "backend"
        if name.endswith((".md", ".mdx")):
            return "documentation"
        if name in {"package.json", "pyproject.toml", "dockerfile", "docker-compose.yml"}:
            return "configuration"
        return "other"

    @staticmethod
    def expand_dependents(
        changed_paths: Set[str], edges: List[dict], max_depth: int = 3
    ) -> Set[str]:
        """Find files that may be affected by changed targets through imports."""
        impacted: Set[str] = set()
        frontier = set(changed_paths)
        for _ in range(max_depth):
            next_frontier: Set[str] = set()
            for edge in edges:
                if edge["target"] in frontier and edge["source"] not in changed_paths:
                    next_frontier.add(edge["source"])
            next_frontier -= impacted
            impacted.update(next_frontier)
            frontier = next_frontier
            if not frontier:
                break
        return impacted

    @staticmethod
    def resolve_import(
        source_path: str, import_text: str, known_paths: Set[str]
    ) -> str | None:
        """Resolve common Python and JS/TS import forms to a known file."""
        text = import_text.strip().rstrip(";")

        if text.startswith("from "):
            module = text[5:].split(" import ", 1)[0].strip()
            if module.startswith("."):
                base = PurePosixPath(source_path).parent
                candidates = [posixpath.normpath(str(base.joinpath(module)))]
            else:
                candidates = [module.replace(".", "/")]
        elif text.startswith("import "):
            if " from " in text:
                module = text.rsplit(" from ", 1)[1].strip().strip("'\"")
            else:
                module = text[7:].split(",", 1)[0].strip().split(" as ", 1)[0]
            if module.startswith("."):
                base = PurePosixPath(source_path).parent
                candidates = [posixpath.normpath(str(base.joinpath(module)))]
            else:
                candidates = [module.replace(".", "/")]
        else:
            marker = "from "
            if marker in text:
                module = text.rsplit(marker, 1)[1].strip().strip("'\"")
            elif "require(" in text:
                module = text.split("require(", 1)[1].split(")", 1)[0].strip("'\"")
            else:
                return None

            if module.startswith("."):
                base = PurePosixPath(source_path).parent
                candidates = [posixpath.normpath(str(base.joinpath(module)))]
            else:
                candidates = [module]

        # Python packages are often rooted below a repository directory such
        # as backend/ or frontend/. Try those roots for absolute module names.
        rooted_candidates = list(candidates)
        for candidate in candidates:
            for root in ("backend", "frontend", "src"):
                rooted_candidates.append(f"{root}/{candidate}")
        candidates = rooted_candidates

        expanded: List[str] = []
        for candidate in candidates:
            candidate = candidate.lstrip("./")
            expanded.extend(
                [
                    candidate,
                    f"{candidate}.py",
                    f"{candidate}.js",
                    f"{candidate}.jsx",
                    f"{candidate}.ts",
                    f"{candidate}.tsx",
                    f"{candidate}/__init__.py",
                    f"{candidate}/index.js",
                    f"{candidate}/index.ts",
                ]
            )

        for candidate in expanded:
            if candidate in known_paths:
                return candidate
        return None
