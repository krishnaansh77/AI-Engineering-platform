"""GitHub repository service — cloning, file listing, language detection."""
import hashlib
import hmac
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import git

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

    def clone_repository(
        self,
        github_url: str,
        pat: str,
        dest_dir: str,
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

        # Derive local directory name from the repo slug
        repo_slug = github_url.rstrip("/").split("/")[-1]
        clone_path = os.path.join(dest_dir, repo_slug)

        if os.path.exists(clone_path):
            logger.info("Repository already cloned at %s — pulling latest", clone_path)
            self.update_repository(clone_path)
            return clone_path

        os.makedirs(dest_dir, exist_ok=True)
        logger.info("Cloning %s → %s", github_url, clone_path)

        git.Repo.clone_from(
            auth_url,
            clone_path,
            depth=50,  # Shallow clone for speed
        )

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
        commit = repo.head.commit
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
