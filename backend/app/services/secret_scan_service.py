"""Opt-in heuristic secret-pattern scanning for indexed repository source files."""
import re
from pathlib import Path
from typing import Dict, List


PATTERNS = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "high"),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "high"),
    ("generic_api_key", re.compile(r"(?i)\b(?:api[_-]?key|secret|token)\s*[:=]\s*['\"][^'\"]{12,}['\"]"), "medium"),
)


class SecretScanService:
    """Find likely committed secrets without returning their values."""

    def scan(self, clone_path: str, files: List[Dict]) -> dict:
        findings = []
        scanned_files = 0
        for file_info in files[:500]:
            path = Path(file_info["path"])
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            scanned_files += 1
            for line_number, line in enumerate(content.splitlines(), start=1):
                for pattern_name, pattern, confidence in PATTERNS:
                    if pattern.search(line):
                        findings.append({
                            "file_path": file_info["relative_path"],
                            "line": line_number,
                            "pattern": pattern_name,
                            "confidence": confidence,
                            "redacted_preview": re.sub(r"(['\"])[^'\"]{4,}(['\"])", r"\1[REDACTED]\2", line.strip())[:240],
                        })
                        break
        return {"heuristic": True, "scanned_files": scanned_files, "finding_count": len(findings), "findings": findings}
