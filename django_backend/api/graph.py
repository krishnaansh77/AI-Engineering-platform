from __future__ import annotations

import posixpath
from pathlib import PurePosixPath

from .models import CodeChunk, SourceFile


def resolve_import(source_path: str, import_text: str, known_paths: set[str]) -> str | None:
    text = import_text.strip().rstrip(";")
    if text.startswith("from "):
        module = text[5:].split(" import ", 1)[0].strip()
    elif text.startswith("import "):
        module = (text.rsplit(" from ", 1)[1].strip().strip("'\"") if " from " in text else text[7:].split(",", 1)[0].strip().split(" as ", 1)[0])
    elif "require(" in text:
        module = text.split("require(", 1)[1].split(")", 1)[0].strip("'\"")
    else:
        return None
    candidates = [module.replace(".", "/")]
    if module.startswith("."):
        candidates = [posixpath.normpath(str(PurePosixPath(source_path).parent.joinpath(module)))]
    rooted = list(candidates)
    for candidate in candidates:
        rooted.extend(f"{root}/{candidate}" for root in ("backend", "frontend", "src"))
    expanded = []
    for candidate in rooted:
        candidate = candidate.lstrip("./")
        expanded.extend([candidate, f"{candidate}.py", f"{candidate}.js", f"{candidate}.jsx", f"{candidate}.ts", f"{candidate}.tsx", f"{candidate}/__init__.py", f"{candidate}/index.js", f"{candidate}/index.ts"])
    return next((candidate for candidate in expanded if candidate in known_paths), None)


def classify_layer(file_path: str) -> str:
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


def build_file_graph(repo_id) -> dict:
    file_paths = sorted(set(SourceFile.objects.filter(repository_id=repo_id).values_list("file_path", flat=True)))
    known_paths = set(file_paths)
    chunks = CodeChunk.objects.filter(repository_id=repo_id)
    edges = set()
    symbols_by_file = {path: [] for path in file_paths}
    for chunk in chunks:
        if chunk.symbol_name:
            symbols_by_file.setdefault(chunk.file_path, []).append({"name": chunk.symbol_name, "type": chunk.chunk_type, "parent": chunk.parent_symbol, "start_line": chunk.start_line, "end_line": chunk.end_line})
        for raw_import in chunk.imports or []:
            target = resolve_import(chunk.file_path, raw_import, known_paths)
            if target and target != chunk.file_path:
                edges.add((chunk.file_path, target, raw_import))
    nodes = [{"id": path, "file_path": path, "symbols": sorted(symbols_by_file.get(path, []), key=lambda item: (item["start_line"], item["name"]))} for path in file_paths]
    edge_list = [{"source": source, "target": target, "import": import_text} for source, target, import_text in sorted(edges)]
    return {"nodes": nodes, "edges": edge_list, "node_count": len(nodes), "edge_count": len(edge_list)}


def build_architecture(repo_id) -> dict:
    graph = build_file_graph(repo_id)
    layers = {}
    file_layers = {}
    for node in graph["nodes"]:
        layer = classify_layer(node["file_path"])
        file_layers[node["id"]] = layer
        layers.setdefault(layer, []).append(node["file_path"])
    links = {}
    for edge in graph["edges"]:
        source, target = file_layers[edge["source"]], file_layers[edge["target"]]
        if source != target:
            links[(source, target)] = links.get((source, target), 0) + 1
    return {"layers": [{"name": name, "file_count": len(paths), "files": sorted(paths)[:8]} for name, paths in sorted(layers.items(), key=lambda item: (-len(item[1]), item[0]))], "cross_layer_links": [{"source": source, "target": target, "edge_count": count} for (source, target), count in sorted(links.items())]}


def build_test_summary(repo_id) -> dict:
    graph = build_file_graph(repo_id)
    paths = [node["file_path"] for node in graph["nodes"]]
    test_files = {path for path in paths if classify_layer(path) == "tests"}
    source_files = set(paths) - test_files
    tested = set()
    for edge in graph["edges"]:
        if edge["source"] in test_files and edge["target"] in source_files:
            tested.add(edge["target"])
    source_by_stem = {PurePosixPath(path).stem.lower(): path for path in source_files}
    for test_path in test_files:
        stem = PurePosixPath(test_path).stem.lower()
        for candidate in (stem.removeprefix("test_"), stem.removesuffix("_test")):
            if candidate in source_by_stem:
                tested.add(source_by_stem[candidate])
    untested = sorted(source_files - tested)
    return {"test_file_count": len(test_files), "source_file_count": len(source_files), "tested_file_count": len(tested), "untested_file_count": len(untested), "tested_files": sorted(tested), "untested_files": untested}


def build_tour(repo_id) -> dict:
    graph = build_file_graph(repo_id)
    counts = {node["id"]: 0 for node in graph["nodes"]}
    for edge in graph["edges"]:
        counts[edge["source"]] += 1
        counts[edge["target"]] += 1
    key_files = []
    for node in sorted(graph["nodes"], key=lambda item: (-counts[item["id"]], item["file_path"]))[:8]:
        key_files.append({"file_path": node["file_path"], "connections": counts[node["id"]], "symbols": [symbol["name"] for symbol in node.get("symbols", [])[:6]], "layer": classify_layer(node["file_path"])})
    return {"file_count": graph["node_count"], "relationship_count": graph["edge_count"], "key_files": key_files}


def build_debt(repo_id) -> dict:
    graph = build_file_graph(repo_id)
    chunks = list(CodeChunk.objects.filter(repository_id=repo_id))
    counts = {node["id"]: 0 for node in graph["nodes"]}
    for edge in graph["edges"]:
        counts[edge["source"]] += 1
        counts[edge["target"]] += 1
    max_lines = {}
    for chunk in chunks:
        max_lines[chunk.file_path] = max(max_lines.get(chunk.file_path, 0), max(0, chunk.end_line - chunk.start_line + 1))
    signals = [{"file_path": path, "signal": "high connectivity", "value": count, "unit": "links"} for path, count in sorted(counts.items(), key=lambda item: -item[1])[:5] if count > 0]
    signals.extend({"file_path": path, "signal": "large code chunk", "value": lines, "unit": "lines"} for path, lines in sorted(max_lines.items(), key=lambda item: -item[1])[:5] if lines >= 80)
    unique = {(item["file_path"], item["signal"]): item for item in signals}
    return {"signals": sorted(unique.values(), key=lambda item: (-item["value"], item["file_path"])), "files_analyzed": len(graph["nodes"]), "chunks_analyzed": len(chunks)}


def build_documentation_quality(repo_id) -> dict:
    symbols = [chunk for chunk in CodeChunk.objects.filter(repository_id=repo_id) if chunk.symbol_name and chunk.symbol_name != "__imports__"]
    documented = [chunk for chunk in symbols if chunk.docstring and chunk.docstring.strip()]
    gaps = {}
    for chunk in symbols:
        if not chunk.docstring or not chunk.docstring.strip():
            gaps[chunk.file_path] = gaps.get(chunk.file_path, 0) + 1
    return {"symbol_count": len(symbols), "documented_symbol_count": len(documented), "undocumented_symbol_count": len(symbols) - len(documented), "coverage": round(len(documented) / len(symbols), 3) if symbols else 0, "gaps": [{"file_path": path, "undocumented_symbols": count} for path, count in sorted(gaps.items(), key=lambda item: (-item[1], item[0]))[:10]]}
