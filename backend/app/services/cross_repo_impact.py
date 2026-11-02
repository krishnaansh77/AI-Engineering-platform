"""Extract declared package identities and dependencies for cross-repo review."""
import json
import re
import tomllib
from pathlib import Path


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.strip().lower())


def repository_packages(root_path: str) -> tuple[set[str], set[str]]:
    """Return package identities and declared direct dependencies from common manifests."""
    root = Path(root_path)
    identities: set[str] = set()
    dependencies: set[str] = set()
    package_json = root / "package.json"
    if package_json.is_file():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
            if data.get("name"):
                identities.add(_normalize(data["name"]))
            for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                dependencies.update(_normalize(name) for name in data.get(section, {}))
        except (OSError, ValueError):
            pass
    for manifest in (root / "pyproject.toml", root / "Cargo.toml"):
        if not manifest.is_file():
            continue
        try:
            data = tomllib.loads(manifest.read_text(encoding="utf-8"))
            section = data.get("project", {}) if manifest.name == "pyproject.toml" else data.get("package", {})
            if section.get("name"):
                identities.add(_normalize(section["name"]))
            raw = section.get("dependencies", {})
            if isinstance(raw, list):
                dependencies.update(_normalize(re.split(r"[<>=!~\[]", item, maxsplit=1)[0]) for item in raw)
            elif isinstance(raw, dict):
                dependencies.update(_normalize(name) for name in raw)
            optional = data.get("project", {}).get("optional-dependencies", {})
            for group in optional.values():
                dependencies.update(_normalize(re.split(r"[<>=!~\[]", item, maxsplit=1)[0]) for item in group)
        except (OSError, ValueError, tomllib.TOMLDecodeError):
            pass
    for manifest in (root / "requirements.txt", root / "requirements.in"):
        if manifest.is_file():
            try:
                for line in manifest.read_text(encoding="utf-8").splitlines():
                    line = line.split("#", 1)[0].strip()
                    if line and not line.startswith(("-", ".", "/")):
                        dependencies.add(_normalize(re.split(r"[<>=!~\[]", line, maxsplit=1)[0]))
            except OSError:
                pass
    return identities, {item for item in dependencies if item}
