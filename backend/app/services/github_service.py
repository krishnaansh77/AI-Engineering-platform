"""GitHub repository service — cloning, file listing, language detection."""
import hashlib
import hmac
import logging
import os
import base64
import difflib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import git
import httpx
import asyncio

logger = logging.getLogger(__name__)

# Languages currently supported by the parser
SUPPORTED_EXTENSIONS: Dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
}

# Framework detection heuristics — file presence → framework name
FRAMEWORK_SIGNALS: Dict[str, str] = {
    "package.json": "Node.js",
    "requirements.txt": "Python",
    "pyproject.toml": "Python",
    "setup.py": "Python",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "pom.xml": "Java/Maven",
    "build.gradle": "Java/Gradle",
    "next.config.js": "Next.js",
    "next.config.ts": "Next.js",
    "vite.config.ts": "Vite",
    "vite.config.js": "Vite",
    "angular.json": "Angular",
    "vue.config.js": "Vue.js",
    "fastapi": None,  # Detected by import scanning
    "django": None,
    "flask": None,
}

# Directories to skip
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".next", ".nuxt", "coverage", ".mypy_cache",
    ".pytest_cache", ".tox", "eggs", ".eggs",
}

# Maximum individual file size to parse (bytes)
MAX_FILE_SIZE = 512_000  # 512 KB


class GitHubService:
    """Handles GitHub repository cloning, updating, and file discovery."""

    SUPPORTED_EXTENSIONS = SUPPORTED_EXTENSIONS

    @staticmethod
    def current_commit(clone_path: str) -> str:
        """Return the exact commit checked out for a repository version."""
        return git.Repo(clone_path).head.commit.hexsha

    @staticmethod
    def current_branch(clone_path: str) -> str:
        """Return the checked-out branch name for a default-branch clone."""
        repository = git.Repo(clone_path)
        try:
            return repository.active_branch.name
        except TypeError:
            remote_head = repository.git.symbolic_ref("refs/remotes/origin/HEAD")
            return remote_head.rsplit("/", 1)[-1]

    def clone_repository(
        self,
        github_url: str,
        pat: str,
        dest_dir: str,
        version_ref: str = "default",
    ) -> str:
        """Clone a GitHub repository using a Personal Access Token.

        Args:
            github_url: Public GitHub URL (https://github.com/owner/repo)
            pat: GitHub Personal Access Token with repo scope
            dest_dir: Parent directory where the repo will be cloned

        Returns:
            Absolute path to the cloned repository directory
        """
        # Authenticate if PAT provided; otherwise clone public repository directly
        if pat and pat.strip():
            auth_url = github_url.replace("https://", f"https://{pat.strip()}@")
        else:
            auth_url = github_url

        # Refs are explicit and isolated on disk so concurrent branch indexing
        # cannot change the default checkout or another version's files.
        ref_type = "default"
        ref_name = ""
        if version_ref != "default":
            match = re.fullmatch(r"(branch|tag):([A-Za-z0-9][A-Za-z0-9._/-]{0,199})", version_ref)
            if not match:
                raise ValueError("Version must be 'default', 'branch:<name>', or 'tag:<name>'.")
            ref_type, ref_name = match.groups()
            if (
                any(
                    not part
                    or part.startswith(".")
                    or part.endswith(".")
                    or ".." in part
                    or part.lower().endswith(".lock")
                    for part in ref_name.split("/")
                )
                or "@{" in ref_name
            ):
                raise ValueError("Version reference is not a valid Git ref name.")

        # Derive local directory name from the repo slug. Alternate refs use a
        # stable digest suffix and remain siblings of the default clone.
        repo_slug = github_url.rstrip("/").split("/")[-1]
        if ref_type == "default":
            clone_path = os.path.join(dest_dir, repo_slug)
        else:
            clone_key = f"{github_url.rstrip('/').lower()}#{version_ref}"
            version_key = hashlib.sha256(clone_key.encode("utf-8")).hexdigest()[:12]
            clone_path = os.path.join(dest_dir, f"{repo_slug}-version-{version_key}")

        if os.path.exists(clone_path):
            logger.info("Version checkout already exists at %s", clone_path)
            if ref_type not in {"tag", "default"} and not self.update_repository(clone_path):
                raise RuntimeError("The requested branch could not be refreshed from its remote.")
            if ref_type == "default":
                self.update_repository(clone_path)
            return clone_path

        os.makedirs(dest_dir, exist_ok=True)
        logger.info("Cloning %s → %s", github_url, clone_path)

        clone_options = {"depth": 50}
        if ref_type == "branch":
            clone_options["branch"] = ref_name
            clone_options["depth"] = 1
        elif ref_type == "tag":
            clone_options["depth"] = 1
            clone_options["no_checkout"] = True
        repository = git.Repo.clone_from(auth_url, clone_path, **clone_options)
        if ref_type == "tag":
            tag_ref = f"refs/tags/{ref_name}"
            repository.git.fetch("--depth=1", "origin", f"{tag_ref}:{tag_ref}")
            repository.git.checkout("--detach", tag_ref)

        logger.info("Clone complete: %s", clone_path)
        return clone_path

    def update_repository(self, clone_path: str) -> bool:
        """Pull the latest changes for an already-cloned repository.

        Returns:
            True if the pull succeeded, False otherwise
        """
        try:
            repo = git.Repo(clone_path)
            origin = repo.remotes.origin
            origin.pull()
            logger.info("Updated repository at %s", clone_path)
            return True
        except Exception as e:
            logger.warning("Failed to pull repository at %s: %s", clone_path, e)
            return False

    def list_source_files(self, clone_path: str) -> List[Dict]:
        """Walk the repository and return all supported source files.

        Returns:
            List of dicts with keys: path, relative_path, size, language
        """
        files: List[Dict] = []
        root = Path(clone_path)

        for file_path in root.rglob("*"):
            # Skip directories and non-files
            if not file_path.is_file():
                continue

            # Skip hidden and irrelevant directories
            parts = file_path.relative_to(root).parts
            if any(part in SKIP_DIRS or part.startswith(".") for part in parts):
                continue

            # Check extension
            ext = file_path.suffix.lower()
            language = SUPPORTED_EXTENSIONS.get(ext)
            if not language:
                continue

            # Skip files that are too large
            size = file_path.stat().st_size
            if size > MAX_FILE_SIZE:
                logger.debug("Skipping large file: %s (%d bytes)", file_path, size)
                continue

            relative_path = str(file_path.relative_to(root))
            files.append(
                {
                    "path": str(file_path),
                    "relative_path": relative_path,
                    "size": size,
                    "language": language,
                }
            )

        logger.info("Found %d supported source files in %s", len(files), clone_path)
        return files

    def detect_languages(self, clone_path: str) -> List[str]:
        """Detect programming languages used in the repository.

        Returns:
            Sorted list of language names (e.g. ["javascript", "python", "typescript"])
        """
        lang_counts: Dict[str, int] = {}
        root = Path(clone_path)

        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            parts = file_path.relative_to(root).parts
            if any(part in SKIP_DIRS or part.startswith(".") for part in parts):
                continue
            ext = file_path.suffix.lower()
            lang = SUPPORTED_EXTENSIONS.get(ext)
            if lang:
                lang_counts[lang] = lang_counts.get(lang, 0) + 1

        # Sort by frequency (most common first)
        return sorted(lang_counts, key=lambda l: -lang_counts[l])

    def detect_frameworks(self, clone_path: str) -> List[str]:
        """Detect frameworks by checking for known configuration files.

        Returns:
            List of detected framework names
        """
        root = Path(clone_path)
        frameworks: List[str] = []

        for signal_file, framework_name in FRAMEWORK_SIGNALS.items():
            if framework_name and (root / signal_file).exists():
                frameworks.append(framework_name)

        return list(dict.fromkeys(frameworks))  # deduplicate while preserving order

    def get_file_hash(self, file_path: str) -> str:
        """Compute SHA-256 hash of a file's contents for change detection."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def get_commit_history(self, clone_path: str, limit: int = 20) -> List[Dict]:
        """Return recent commits and the files changed in each commit."""
        repo = git.Repo(clone_path)
        commits: List[Dict] = []
        safe_limit = max(1, min(limit, 100))
        for commit in repo.iter_commits(max_count=safe_limit):
            stats = commit.stats.total
            commits.append(
                {
                    "sha": commit.hexsha,
                    "short_sha": commit.hexsha[:7],
                    "message": (commit.message or "").splitlines()[0][:240],
                    "author": commit.author.name or "Unknown",
                    "committed_at": datetime.fromtimestamp(
                        commit.committed_date, tz=timezone.utc
                    ).isoformat(),
                    "files": sorted(commit.stats.files.keys()),
                    "files_changed": int(stats.get("files", 0)),
                    "insertions": int(stats.get("insertions", 0)),
                    "deletions": int(stats.get("deletions", 0)),
                }
            )
        return commits

    def read_source_file(
        self, clone_path: str, relative_path: str, max_bytes: int = 200_000
    ) -> Dict:
        """Read a bounded repository file while preventing path traversal."""
        root = Path(clone_path).resolve()
        candidate = (root / relative_path).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError("File path must stay inside the repository") from exc
        if not candidate.is_file():
            raise FileNotFoundError(relative_path)
        if candidate.stat().st_size > max_bytes:
            raise ValueError("File is too large to preview")
        return {
            "file_path": str(candidate.relative_to(root)),
            "language": SUPPORTED_EXTENSIONS.get(candidate.suffix.lower(), "text"),
            "content": candidate.read_text(encoding="utf-8", errors="replace"),
        }

    def list_documentation_files(self, clone_path: str, max_files: int = 50) -> List[Dict]:
        """Find repository documentation without indexing it as source code."""
        root = Path(clone_path).resolve()
        documentation: List[Dict] = []
        supported = {".md", ".mdx", ".rst", ".txt"}
        for file_path in sorted(root.rglob("*")):
            if len(documentation) >= max_files or not file_path.is_file():
                break
            relative = file_path.relative_to(root)
            parts = relative.parts
            if any(part in SKIP_DIRS or part.startswith(".") for part in parts):
                continue
            if file_path.suffix.lower() not in supported:
                continue
            if file_path.stat().st_size > 200_000:
                continue
            documentation.append(
                {
                    "file_path": str(relative),
                    "title": file_path.stem.replace("-", " ").replace("_", " ").title(),
                    "size_bytes": file_path.stat().st_size,
                    "content": file_path.read_text(encoding="utf-8", errors="replace"),
                }
            )
        return documentation

    def analyze_latest_commit(self, clone_path: str) -> Dict:
        """Summarize the latest local commit for PR-style review signals."""
        repo = git.Repo(clone_path)
        return self.analyze_commit(clone_path, repo.head.commit.hexsha)

    def analyze_commit(self, clone_path: str, commit_ref: str) -> Dict:
        """Summarize any commit available in the local clone for PR-style review."""
        repo = git.Repo(clone_path)
        commit = repo.commit(commit_ref)
        changed_files = sorted(commit.stats.files.keys())
        test_files = [path for path in changed_files if "test" in Path(path).name.lower() or "tests" in Path(path).parts]
        documentation_files = [path for path in changed_files if Path(path).suffix.lower() in {".md", ".mdx", ".rst"}]
        source_files = [path for path in changed_files if path not in test_files and path not in documentation_files]
        recommendations = []
        if source_files and not test_files:
            recommendations.append("Review or add tests for the changed source files.")
        if source_files and not documentation_files:
            recommendations.append("Check whether developer documentation needs an update.")
        if not recommendations:
            recommendations.append("No obvious test or documentation gaps detected from file names.")
        return {
            "sha": commit.hexsha,
            "short_sha": commit.hexsha[:7],
            "message": (commit.message or "").splitlines()[0][:240],
            "author": commit.author.name or "Unknown",
            "changed_files": changed_files,
            "source_files": source_files,
            "test_files": test_files,
            "documentation_files": documentation_files,
            "insertions": int(commit.stats.total.get("insertions", 0)),
            "deletions": int(commit.stats.total.get("deletions", 0)),
            "recommendations": recommendations,
        }

    def compare_commits(self, clone_path: str, base_ref: str, head_ref: str) -> Dict:
        """Compare two locally available commits and return PR review signals."""
        repo = git.Repo(clone_path)
        if base_ref.startswith("-") or head_ref.startswith("-"):
            raise ValueError("Commit references cannot start with '-'")
        base = repo.commit(base_ref)
        head = repo.commit(head_ref)
        changed_files = [path for path in repo.git.diff("--name-only", f"{base.hexsha}...{head.hexsha}").splitlines() if path]
        numstat = repo.git.diff("--numstat", f"{base.hexsha}...{head.hexsha}").splitlines()
        insertions = 0
        deletions = 0
        for line in numstat:
            parts = line.split("\t", 2)
            if len(parts) >= 2:
                insertions += int(parts[0]) if parts[0].isdigit() else 0
                deletions += int(parts[1]) if parts[1].isdigit() else 0

        test_files = [path for path in changed_files if "test" in Path(path).name.lower() or "tests" in Path(path).parts]
        documentation_files = [path for path in changed_files if Path(path).suffix.lower() in {".md", ".mdx", ".rst"}]
        source_files = [path for path in changed_files if path not in test_files and path not in documentation_files]
        recommendations = []
        if source_files and not test_files:
            recommendations.append("Review or add tests for the changed source files.")
        if source_files and not documentation_files:
            recommendations.append("Check whether developer documentation needs an update.")
        if not recommendations:
            recommendations.append("No obvious test or documentation gaps detected from file names.")
        return {
            "base_sha": base.hexsha,
            "base_short_sha": base.hexsha[:7],
            "head_sha": head.hexsha,
            "head_short_sha": head.hexsha[:7],
            "message": (head.message or "").splitlines()[0][:240],
            "author": head.author.name or "Unknown",
            "changed_files": sorted(changed_files),
            "source_files": source_files,
            "test_files": test_files,
            "documentation_files": documentation_files,
            "insertions": insertions,
            "deletions": deletions,
            "recommendations": recommendations,
        }

    def compare_version_checkouts(
        self,
        base_path: str,
        head_path: str,
        max_files: int = 30,
        max_diff_chars: int = 24_000,
    ) -> Dict:
        """Compare two isolated version checkouts without fetching or mutating either one."""
        base_repo = git.Repo(base_path)
        head_repo = git.Repo(head_path)
        base_commit = base_repo.head.commit
        head_commit = head_repo.head.commit
        base_blobs = {
            item.path: item
            for item in base_commit.tree.traverse()
            if item.type == "blob"
        }
        head_blobs = {
            item.path: item
            for item in head_commit.tree.traverse()
            if item.type == "blob"
        }
        changed_paths = sorted(
            path
            for path in base_blobs.keys() | head_blobs.keys()
            if path not in base_blobs
            or path not in head_blobs
            or base_blobs[path].hexsha != head_blobs[path].hexsha
        )

        changes = []
        remaining_chars = max_diff_chars
        for path in changed_paths[:max_files]:
            before = base_blobs.get(path)
            after = head_blobs.get(path)
            status = "added" if before is None else "deleted" if after is None else "modified"
            item = {
                "file_path": path,
                "status": status,
                "base_lines": 0,
                "head_lines": 0,
                "base_citation": None,
                "head_citation": None,
                "diff": "",
            }
            try:
                before_bytes = before.data_stream.read(200_001) if before else b""
                after_bytes = after.data_stream.read(200_001) if after else b""
                if len(before_bytes) > 200_000 or len(after_bytes) > 200_000:
                    item["omitted_reason"] = "File exceeds the 200 KB comparison limit."
                elif b"\0" in before_bytes or b"\0" in after_bytes:
                    item["omitted_reason"] = "Binary files are listed but not shown as text diffs."
                else:
                    before_text = before_bytes.decode("utf-8")
                    after_text = after_bytes.decode("utf-8")
                    item["base_lines"] = len(before_text.splitlines())
                    item["head_lines"] = len(after_text.splitlines())
                    diff = "".join(difflib.unified_diff(
                        before_text.splitlines(keepends=True),
                        after_text.splitlines(keepends=True),
                        fromfile=f"base/{path}",
                        tofile=f"head/{path}",
                        n=3,
                    ))
                    if len(diff) > remaining_chars:
                        item["omitted_reason"] = "Total diff display limit reached."
                    else:
                        item["diff"] = diff
                        remaining_chars -= len(diff)
                        base_ranges = []
                        head_ranges = []
                        for old_start, old_count, new_start, new_count in re.findall(
                            r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@",
                            diff,
                            re.MULTILINE,
                        ):
                            old_count = int(old_count or 1)
                            new_count = int(new_count or 1)
                            if old_count:
                                base_ranges.append(f"{old_start}-{int(old_start) + old_count - 1}")
                            if new_count:
                                head_ranges.append(f"{new_start}-{int(new_start) + new_count - 1}")
                        item["base_citation"] = {"file_path": path, "line_ranges": base_ranges}
                        item["head_citation"] = {"file_path": path, "line_ranges": head_ranges}
            except (UnicodeDecodeError, OSError, ValueError):
                item["omitted_reason"] = "File is not readable as UTF-8 text."
            changes.append(item)

        return {
            "base_sha": base_commit.hexsha,
            "head_sha": head_commit.hexsha,
            "changed_paths": changed_paths,
            "changed_file_count": len(changed_paths),
            "shown_file_count": len(changes),
            "truncated": len(changed_paths) > len(changes)
            or any(change.get("omitted_reason") for change in changes),
            "changes": changes,
        }

    async def list_issues(self, github_url: str, pat: str = "", limit: int = 20, state: str = "open") -> List[Dict]:
        """Fetch GitHub issues with bounded retries, excluding pull requests."""
        parts = [part for part in github_url.rstrip("/").split("/") if part]
        if len(parts) < 2:
            raise ValueError("Invalid GitHub repository URL")
        api_url = f"https://api.github.com/repos/{parts[-2]}/{parts[-1]}/issues"
        headers = {"Accept": "application/vnd.github+json"}
        if pat.strip():
            headers["Authorization"] = f"Bearer {pat.strip()}"
        if state not in {"open", "closed", "all"}:
            raise ValueError("Issue state must be open, closed, or all")
        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            response = None
            for attempt in range(3):
                try:
                    response = await client.get(api_url, params={"state": state, "per_page": max(1, min(limit, 50))})
                    if response.status_code == 429 or response.status_code >= 500:
                        if attempt < 2:
                            await asyncio.sleep(0.25 * (2 ** attempt))
                            continue
                    response.raise_for_status()
                    break
                except (httpx.TimeoutException, httpx.NetworkError):
                    if attempt == 2:
                        raise
                    await asyncio.sleep(0.25 * (2 ** attempt))
            if response is None:
                raise httpx.HTTPError("GitHub did not return a response")
            issues = response.json()
        return [
            {
                "number": issue["number"],
                "title": issue["title"],
                "body": issue.get("body") or "",
                "html_url": issue["html_url"],
                "labels": [label["name"] for label in issue.get("labels", [])],
                "created_at": issue["created_at"],
            }
            for issue in issues
            if "pull_request" not in issue
        ]

    async def save_documentation_file(
        self,
        github_url: str,
        pat: str,
        file_path: str,
        content: str,
        branch: str,
        commit_message: str,
        confirm: bool = False,
    ) -> Dict:
        """Preview or explicitly commit a bounded documentation file to GitHub.

        A preview never mutates GitHub. A commit requires ``confirm=True`` and
        includes the current blob SHA so an existing file cannot be silently
        overwritten after it changed remotely.
        """
        if not pat.strip():
            raise PermissionError("GITHUB_PAT is required to save documentation to GitHub.")
        normalized_path = file_path.strip().strip("/")
        if not normalized_path or any(part in {"", ".", ".."} for part in normalized_path.split("/")):
            raise ValueError("Documentation path must be a repository-relative file path.")
        if not normalized_path.lower().endswith((".md", ".mdx", ".rst")):
            raise ValueError("Documentation saves are limited to .md, .mdx, and .rst files.")
        if len(normalized_path) > 500 or len(content.encode("utf-8")) > 50_000:
            raise ValueError("Documentation path or content exceeds the safe limit.")
        if not re.fullmatch(r"[A-Za-z0-9._/-]+", branch) or len(branch) > 200:
            raise ValueError("Branch must be a valid GitHub branch name.")
        if not commit_message.strip() or len(commit_message) > 200:
            raise ValueError("Commit message must be between 1 and 200 characters.")

        parts = [part for part in github_url.rstrip("/").split("/") if part]
        if len(parts) < 2:
            raise ValueError("Invalid GitHub repository URL")
        owner, repo = parts[-2], parts[-1]
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{normalized_path}"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {pat.strip()}",
        }
        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            response = await client.get(api_url, params={"ref": branch})
            existing_content = ""
            current_sha = None
            if response.status_code == 200:
                payload = response.json()
                current_sha = payload.get("sha")
                try:
                    existing_content = base64.b64decode(payload.get("content", "")).decode("utf-8")
                except (ValueError, UnicodeDecodeError) as exc:
                    raise ValueError("The existing documentation file is not valid UTF-8 text.") from exc
            elif response.status_code != 404:
                response.raise_for_status()

            diff = "".join(difflib.unified_diff(
                existing_content.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=f"a/{normalized_path}",
                tofile=f"b/{normalized_path}",
            ))
            result = {
                "file_path": normalized_path,
                "branch": branch,
                "commit_message": commit_message.strip(),
                "existing": existing_content,
                "diff": diff,
                "current_sha": current_sha,
                "changed": existing_content != content,
                "saved": False,
            }
            if not confirm:
                return result
            if not result["changed"]:
                raise ValueError("The generated documentation is identical to the current file.")

            body = {
                "message": commit_message.strip(),
                "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
                "branch": branch,
            }
            if current_sha:
                body["sha"] = current_sha
            saved_response = await client.put(api_url, json=body)
            saved_response.raise_for_status()
            saved_payload = saved_response.json()
            result.update({
                "saved": True,
                "commit_sha": saved_payload.get("commit", {}).get("sha"),
                "commit_url": saved_payload.get("commit", {}).get("html_url"),
            })
            return result

    def verify_webhook_signature(
        self, payload: bytes, signature_header: str, secret: str
    ) -> bool:
        """Verify a GitHub webhook HMAC-SHA256 signature.

        Args:
            payload: Raw request body bytes
            signature_header: Value of the X-Hub-Signature-256 header
            secret: Webhook secret configured in GitHub

        Returns:
            True if the signature is valid
        """
        if not signature_header.startswith("sha256="):
            return False
        expected_sig = signature_header[len("sha256="):]
        computed_sig = hmac.new(
            secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected_sig, computed_sig)
