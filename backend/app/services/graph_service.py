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
        for chunk in chunks_result.scalars().all():
            source = chunk.file_path
            for raw_import in chunk.imports or []:
                target = self.resolve_import(source, raw_import, known_paths)
                if target and target != source:
                    edges.add((source, target, raw_import))

        nodes = [{"id": path, "file_path": path} for path in file_paths]
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
