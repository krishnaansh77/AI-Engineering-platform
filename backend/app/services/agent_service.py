"""Bounded repository agent that selects and runs existing analysis tools."""
from __future__ import annotations

import inspect
import json
import re
from typing import TYPE_CHECKING, Callable, Any

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.models.repository import Repository


async def run_optional_tool(name: str, operation: Callable[[], Any]) -> dict:
    """Isolate an optional tool failure while preserving an explicit result."""
    try:
        result = operation()
        if inspect.isawaitable(result):
            result = await result
        return {"tool": name, **result}
    except Exception:
        return {"tool": name, "error": "This repository tool is unavailable."}


class RepositoryAgent:
    """Run a small, transparent tool plan and return evidence for synthesis."""

    @staticmethod
    def plan_tools(question: str) -> list[str]:
        """Choose bounded read-only tools using transparent question cues."""
        lowered = question.casefold()
        tools = ["search_code"]
        if any(word in lowered for word in ("commit", "history", "changed", "recent", "when")):
            tools.append("get_history")
        if any(word in lowered for word in ("impact", "affect", "depend", "downstream", "break")):
            tools.append("get_impact")
        if any(word in lowered for word in ("test", "coverage", "untested")):
            tools.append("get_tests")
        if re.search(r"(?:[\w.-]+/)+[\w.-]+\.[A-Za-z0-9]+", question):
            tools.append("get_file")
        return tools

    async def run(
        self,
        repo: Repository,
        question: str,
        db: AsyncSession,
        top_k: int,
        version_ref: str = "default",
    ) -> tuple[list, list[dict]]:
        from app.services.github_service import GitHubService
        from app.services.graph_service import DependencyGraphService
        from app.services.retrieval_service import RetrievalService
        from app.models.repository_version import RepositoryVersion
        from sqlalchemy import select

        version = await db.scalar(select(RepositoryVersion).where(
            RepositoryVersion.repository_id == repo.id,
            RepositoryVersion.version_ref == version_ref,
        ))
        clone_path = repo.clone_path if version_ref == "default" else (version.clone_path if version else None)

        tools = self.plan_tools(question)
        path_match = re.search(r"(?:[\w.-]+/)+[\w.-]+\.[A-Za-z0-9]+", question)
        if path_match:
            tools.append("get_file")

        retrieved = await RetrievalService().retrieve(
            query=question,
            repo_id=repo.id,
            db=db,
            top_k=20,
            final_k=top_k,
            version_ref=version_ref,
        )
        evidence: list[dict] = [{
            "tool": "search_code",
            "results": [{
                "file_path": chunk.file_path,
                "symbol": chunk.symbol_name,
                "lines": [chunk.start_line, chunk.end_line],
                "snippet": chunk.content[:1800],
            } for chunk in retrieved],
        }]
        if "get_history" in tools and clone_path:
            evidence.append(await run_optional_tool(
                "get_history",
                lambda: {"commits": GitHubService().get_commit_history(clone_path, 5)},
            ))
        if "get_impact" in tools and clone_path:
            try:
                graph = await DependencyGraphService().build_file_graph(repo.id, db, version_ref=version_ref)
                latest = GitHubService().analyze_latest_commit(clone_path)
                changed = set(latest.get("source_files", latest.get("changed_files", [])))
                changed.intersection_update(node["id"] for node in graph["nodes"])
                impact = sorted(DependencyGraphService.expand_dependents(changed, graph["edges"]))
                evidence.append({"tool": "get_impact", "commit": latest.get("short_sha"), "changed_files": sorted(changed), "impacted_files": impact})
            except Exception:
                evidence.append({"tool": "get_impact", "error": "Recent change impact is unavailable."})
        if "get_tests" in tools:
            async def get_test_summary():
                return await DependencyGraphService().build_test_summary(repo.id, db, version_ref=version_ref)
            evidence.append(await run_optional_tool("get_tests", get_test_summary))
        if "get_file" in tools and clone_path:
            try:
                source = GitHubService().read_source_file(clone_path, path_match.group(0), max_bytes=12_000)
                evidence.append({"tool": "get_file", "file_path": source["file_path"], "content": source["content"][:8000]})
            except (FileNotFoundError, ValueError):
                evidence.append({"tool": "get_file", "error": "The requested path was not found in the indexed repository."})
        return retrieved, evidence

    @staticmethod
    def evidence_prompt(question: str, evidence: list[dict]) -> str:
        payload = json.dumps(evidence, ensure_ascii=False, default=str)[:8000]
        return (
            f"{question}\n\nAgent tool evidence (JSON):\n{payload}\n\n"
            "Use only this evidence and the cited code context. State clearly when a tool did not provide enough evidence. "
            "Do not claim that a candidate impact is confirmed."
        )
