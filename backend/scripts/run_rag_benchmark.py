"""Run a repository retrieval benchmark through the local API.

Example:
    python backend/scripts/run_rag_benchmark.py --repo-id UUID
"""
import argparse
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BENCHMARK = Path(__file__).resolve().parents[2] / "docs" / "rag-benchmark.example.json"


def load_benchmark(path: Path) -> dict:
    with path.open(encoding="utf-8") as benchmark_file:
        payload = json.load(benchmark_file)
    if not payload.get("cases"):
        raise ValueError("Benchmark must contain at least one case")
    return payload


def run(base_url: str, repo_id: str, payload: dict) -> dict:
    request = Request(
        f"{base_url.rstrip('/')}/repos/{repo_id}/evaluate",
        data=json.dumps({"cases": payload["cases"], "top_k": payload.get("top_k", 5)}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-id", required=True, help="Indexed repository UUID")
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--base-url", default="http://localhost:8000/api")
    parser.add_argument("--min-recall", type=float, default=None)
    parser.add_argument("--min-mrr", type=float, default=None)
    args = parser.parse_args()

    try:
        payload = load_benchmark(args.benchmark)
        result = run(args.base_url, args.repo_id, payload)
    except (OSError, ValueError, HTTPError, URLError, json.JSONDecodeError) as exc:
        print(f"Benchmark failed: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    summary = result["summary"]
    failed = (
        args.min_recall is not None and summary["recall_at_k"] < args.min_recall
    ) or (
        args.min_mrr is not None and summary["mrr"] < args.min_mrr
    )
    if failed:
        print("Benchmark quality threshold failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
