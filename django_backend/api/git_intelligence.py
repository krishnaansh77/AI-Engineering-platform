from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import git


def _classify_files(changed_files: list[str]) -> tuple[list[str], list[str], list[str]]:
    tests = [path for path in changed_files if "test" in Path(path).name.lower() or "tests" in Path(path).parts]
    docs = [path for path in changed_files if Path(path).suffix.lower() in {".md", ".mdx", ".rst"}]
    source = [path for path in changed_files if path not in tests and path not in docs]
    return source, tests, docs


def _recommendations(source: list[str], tests: list[str], docs: list[str]) -> list[str]:
    recommendations = []
    if source and not tests:
        recommendations.append("Review or add tests for the changed source files.")
    if source and not docs:
        recommendations.append("Check whether developer documentation needs an update.")
    return recommendations or ["No obvious test or documentation gaps detected from file names."]


def history(clone_path: str, limit: int = 20) -> list[dict]:
    repo = git.Repo(clone_path)
    commits = []
    for commit in repo.iter_commits(max_count=max(1, min(limit, 100))):
        stats = commit.stats.total
        commits.append({
            "sha": commit.hexsha,
            "short_sha": commit.hexsha[:7],
            "message": (commit.message or "").splitlines()[0][:240],
            "author": commit.author.name or "Unknown",
            "committed_at": datetime.fromtimestamp(commit.committed_date, tz=timezone.utc).isoformat(),
            "files": sorted(commit.stats.files.keys()),
            "files_changed": int(stats.get("files", 0)),
            "insertions": int(stats.get("insertions", 0)),
            "deletions": int(stats.get("deletions", 0)),
        })
    return commits


def analyze_commit(clone_path: str, commit_ref: str) -> dict:
    if commit_ref.startswith("-"):
        raise ValueError("Commit references cannot start with '-'")
    commit = git.Repo(clone_path).commit(commit_ref)
    changed_files = sorted(commit.stats.files.keys())
    source, tests, docs = _classify_files(changed_files)
    return {
        "sha": commit.hexsha,
        "short_sha": commit.hexsha[:7],
        "message": (commit.message or "").splitlines()[0][:240],
        "author": commit.author.name or "Unknown",
        "changed_files": changed_files,
        "source_files": source,
        "test_files": tests,
        "documentation_files": docs,
        "insertions": int(commit.stats.total.get("insertions", 0)),
        "deletions": int(commit.stats.total.get("deletions", 0)),
        "recommendations": _recommendations(source, tests, docs),
    }


def compare_commits(clone_path: str, base_ref: str, head_ref: str) -> dict:
    if base_ref.startswith("-") or head_ref.startswith("-"):
        raise ValueError("Commit references cannot start with '-'")
    repo = git.Repo(clone_path)
    base, head = repo.commit(base_ref), repo.commit(head_ref)
    changed_files = [path for path in repo.git.diff("--name-only", f"{base.hexsha}...{head.hexsha}").splitlines() if path]
    insertions = deletions = 0
    for line in repo.git.diff("--numstat", f"{base.hexsha}...{head.hexsha}").splitlines():
        parts = line.split("\t", 2)
        if len(parts) >= 2:
            insertions += int(parts[0]) if parts[0].isdigit() else 0
            deletions += int(parts[1]) if parts[1].isdigit() else 0
    source, tests, docs = _classify_files(sorted(changed_files))
    return {
        "base_sha": base.hexsha,
        "base_short_sha": base.hexsha[:7],
        "head_sha": head.hexsha,
        "head_short_sha": head.hexsha[:7],
        "message": (head.message or "").splitlines()[0][:240],
        "author": head.author.name or "Unknown",
        "changed_files": sorted(changed_files),
        "source_files": source,
        "test_files": tests,
        "documentation_files": docs,
        "insertions": insertions,
        "deletions": deletions,
        "recommendations": _recommendations(source, tests, docs),
    }
