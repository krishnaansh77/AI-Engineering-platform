"""Bounded repository agent that selects and runs existing analysis tools."""
import json
import re
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository import Repository
from app.services.github_service import GitHubService
from app.services.graph_service import DependencyGraphService
from app.services.retrieval_service import RetrievalService


class RepositoryAgent:
    """Run a small, transparent tool plan and return evidence for synthesis."""

    async def run(self, repo: Repository, question: str, db: AsyncSession, top_k: int) -> tuple[list, list[dict]]:
        lowered = question.casefold()
        tools = ["search_code"]
        if any(word in lowered for word in ("commit", "history", "changed", "recent", "when")):
            tools.append("get_history")
        if any(word in lowered for word in ("impact", "affect", "depend", "downstream", "break")):
            tools.append("get_impact")
        if any(word in lowered for word in ("test", "coverage", "untested")):
            tools.append("get_tests")
        path_match = re.search(r"(?:[\w.-]+/)+[\w.-]+\.[A-Za-z0-9]+", question)
        if path_match:
            tools.append("get_file")

        retrieved = await RetrievalService().retrieve(
            query=question, repo_id=repo.id, db=db, top_k=20, final_k=top_k
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
        if "get_history" in tools and repo.clone_path:
            evidence.append({"tool": "get_history", "commits": GitHubService().get_commit_history(repo.clone_path, 5)})
        if "get_impact" in tools and repo.clone_path:
            graph = await DependencyGraphService().build_file_graph(repo.id, db)
            latest = GitHubService().analyze_latest_commit(repo.clone_path)
            changed = set(latest.get("source_files", latest.get("changed_files", [])))
            changed.intersection_update(node["id"] for node in graph["nodes"])
            impact = sorted(DependencyGraphService.expand_dependents(changed, graph["edges"]))
            evidence.append({"tool": "get_impact", "commit": latest.get("short_sha"), "changed_files": sorted(changed), "impacted_files": impact})
        if "get_tests" in tools:
            evidence.append({"tool": "get_tests", **(await DependencyGraphService().build_test_summary(repo.id, db))})
        if "get_file" in tools and repo.clone_path:
            try:
                source = GitHubService().read_source_file(repo.clone_path, path_match.group(0), max_bytes=12_000)
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
