"""Measure advisory code complexity signals for KCS-14 refactor closeouts."""

from __future__ import annotations

import argparse
import ast
import json
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from radon.complexity import cc_visit
from radon.metrics import mi_visit

JsonDict = dict[str, Any]

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATHS = ("src", "tests", "scripts")
DEFAULT_GRAPH_PATH = "docs/internal/engineering-process/code-review-graph.json"
DEFAULT_THRESHOLD = 7
SNAPSHOT_SCHEMA_VERSION = "kcs_complexity_snapshot_v1"
INTERNAL_IMPORT_PREFIXES = ("kcs_adapters", "kcs_core", "tests", "scripts")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    paths = tuple(_repo_path(path) for path in args.paths)
    graph_path = _repo_path(args.graph) if args.graph else None
    snapshot = measure_complexity(
        paths=paths,
        graph_path=graph_path,
        threshold=args.threshold,
    )
    baseline = _load_json(_repo_path(args.baseline)) if args.baseline else None
    if baseline is not None:
        _ensure_compatible_baseline(baseline, snapshot)
        snapshot["delta_from_baseline"] = _summary_delta(
            baseline["summary"],
            snapshot["summary"],
        )
    if args.write_snapshot:
        output_path = _repo_path(args.write_snapshot)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.format == "json":
        print(json.dumps(snapshot, indent=2, sort_keys=True))
    else:
        print(_format_text(snapshot))
    return 0


def measure_complexity(
    *,
    paths: Sequence[Path],
    graph_path: Path | None,
    threshold: int,
) -> JsonDict:
    files = tuple(_python_files(paths))
    modules = _module_map(files)
    graph_nodes = _graph_file_nodes(graph_path) if graph_path else {}
    file_metrics = [
        _measure_file(
            path,
            modules=modules,
            graph_nodes=graph_nodes,
            threshold=threshold,
        )
        for path in files
    ]
    groups = _summaries_by(file_metrics, key_name="group")
    nodes = _summaries_by(file_metrics, key_name="graph_node")
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "path_root": "repository-relative",
        "paths": [str(path.relative_to(ROOT)) for path in paths],
        "graph_path": str(graph_path.relative_to(ROOT)) if graph_path else None,
        "threshold": threshold,
        "summary": _summarize(file_metrics),
        "groups": groups,
        "nodes": nodes,
        "high_complexity_functions": _high_complexity_functions(file_metrics),
    }


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Measure advisory complexity, coupling, and interface-surface "
            "signals for refactor closeouts."
        )
    )
    parser.add_argument("--paths", nargs="+", default=list(DEFAULT_PATHS))
    parser.add_argument("--graph", default=DEFAULT_GRAPH_PATH)
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD)
    parser.add_argument("--baseline")
    parser.add_argument("--write-snapshot")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def _repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def _load_json(path: Path) -> JsonDict:
    return json.loads(path.read_text(encoding="utf-8"))


def _python_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            yield path
            continue
        if path.is_dir():
            yield from sorted(
                item
                for item in path.rglob("*.py")
                if "__pycache__" not in item.parts
            )


def _module_map(files: Sequence[Path]) -> dict[str, str]:
    modules: dict[str, str] = {}
    for path in files:
        module = _module_name(path)
        if module:
            modules[module] = _rel(path)
    return modules


def _module_name(path: Path) -> str:
    rel = path.relative_to(ROOT)
    if rel.parts[0] == "src":
        parts = rel.parts[1:]
    else:
        parts = rel.parts
    stem_parts = parts[:-1] + (Path(parts[-1]).stem,)
    if stem_parts[-1] == "__init__":
        stem_parts = stem_parts[:-1]
    return ".".join(stem_parts)


def _graph_file_nodes(graph_path: Path | None) -> dict[str, str]:
    if graph_path is None or not graph_path.exists():
        return {}
    graph = _load_json(graph_path)
    file_nodes: dict[str, str] = {}
    for node in graph["nodes"]:
        node_id = node["id"]
        for file_entry in node["files"]:
            file_nodes[file_entry["path"]] = node_id
        for test_path in node["related_tests"]:
            file_nodes.setdefault(test_path, node_id)
    return file_nodes


def _measure_file(
    path: Path,
    *,
    modules: Mapping[str, str],
    graph_nodes: Mapping[str, str],
    threshold: int,
) -> JsonDict:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    rel_path = _rel(path)
    blocks = cc_visit(source)
    import_edges = _import_edges(tree, source_path=rel_path, modules=modules)
    public_defs, all_exports = _interface_surface(tree)
    return {
        "path": rel_path,
        "group": _path_group(path),
        "graph_node": graph_nodes.get(rel_path, "unmapped"),
        "cc_blocks": [
            _cc_block(path=rel_path, block=block, threshold=threshold)
            for block in blocks
        ],
        "import_edges": sorted(import_edges),
        "mi": mi_visit(source, True),
        "public_defs": sorted(public_defs),
        "all_exports": sorted(all_exports),
    }


def _cc_block(*, path: str, block: Any, threshold: int) -> JsonDict:
    qualname = getattr(block, "fullname", None) or getattr(block, "name", "<unknown>")
    complexity = int(block.complexity)
    return {
        "path": path,
        "qualname": qualname,
        "lineno": int(getattr(block, "lineno", 0)),
        "cc": complexity,
        "above_threshold": complexity > threshold,
    }


def _import_edges(
    tree: ast.AST,
    *,
    source_path: str,
    modules: Mapping[str, str],
) -> set[str]:
    edges: set[str] = set()
    for module in _imported_modules(tree):
        target = _resolve_module(module, modules)
        if target and target != source_path:
            edges.add(target)
    return edges


def _imported_modules(tree: ast.AST) -> Iterable[str]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module
            for alias in node.names:
                yield f"{node.module}.{alias.name}"


def _resolve_module(module: str, modules: Mapping[str, str]) -> str | None:
    if not module.startswith(INTERNAL_IMPORT_PREFIXES):
        return None
    parts = module.split(".")
    for index in range(len(parts), 0, -1):
        candidate = ".".join(parts[:index])
        if candidate in modules:
            return modules[candidate]
    return None


def _interface_surface(tree: ast.AST) -> tuple[set[str], set[str]]:
    public_defs: set[str] = set()
    all_exports: set[str] = set()
    for node in tree.body if isinstance(tree, ast.Module) else ():
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            _add_public(public_defs, node.name)
        elif isinstance(node, ast.Assign):
            all_exports.update(_all_exports(node))
            for target in node.targets:
                _add_assign_target(public_defs, target)
        elif isinstance(node, ast.AnnAssign):
            _add_assign_target(public_defs, node.target)
    return public_defs, all_exports


def _add_public(names: set[str], name: str) -> None:
    if not name.startswith("_"):
        names.add(name)


def _add_assign_target(names: set[str], target: ast.expr) -> None:
    if isinstance(target, ast.Name):
        _add_public(names, target.id)


def _all_exports(node: ast.Assign) -> set[str]:
    is_all_assignment = any(
        isinstance(target, ast.Name) and target.id == "__all__"
        for target in node.targets
    )
    if not is_all_assignment:
        return set()
    if not isinstance(node.value, ast.List | ast.Tuple):
        return set()
    return {
        item.value
        for item in node.value.elts
        if isinstance(item, ast.Constant) and isinstance(item.value, str)
    }


def _summaries_by(file_metrics: Sequence[JsonDict], *, key_name: str) -> JsonDict:
    grouped: dict[str, list[JsonDict]] = defaultdict(list)
    for metric in file_metrics:
        grouped[str(metric[key_name])].append(metric)
    return {
        key: _summarize(tuple(metrics))
        for key, metrics in sorted(grouped.items())
    }


def _summarize(file_metrics: Sequence[JsonDict]) -> JsonDict:
    blocks = [block for metric in file_metrics for block in metric["cc_blocks"]]
    cc_total = sum(block["cc"] for block in blocks)
    import_edges = {
        (metric["path"], edge)
        for metric in file_metrics
        for edge in metric["import_edges"]
    }
    return {
        "files_scanned": len(file_metrics),
        "functions_total": len(blocks),
        "cc_average": round(cc_total / len(blocks), 2) if blocks else 0.0,
        "max_cc": max((block["cc"] for block in blocks), default=0),
        "high_complexity_functions": sum(
            1 for block in blocks if block["above_threshold"]
        ),
        "mi_average": _average(metric["mi"] for metric in file_metrics),
        "import_edges": len(import_edges),
        "public_defs": sum(len(metric["public_defs"]) for metric in file_metrics),
        "all_exports": sum(len(metric["all_exports"]) for metric in file_metrics),
    }


def _average(values: Iterable[float]) -> float:
    items = list(values)
    return round(sum(items) / len(items), 2) if items else 0.0


def _high_complexity_functions(file_metrics: Sequence[JsonDict]) -> list[JsonDict]:
    blocks = [
        block
        for metric in file_metrics
        for block in metric["cc_blocks"]
        if block["above_threshold"]
    ]
    return sorted(blocks, key=lambda item: (-item["cc"], item["path"], item["lineno"]))


def _summary_delta(baseline: Mapping[str, Any], current: Mapping[str, Any]) -> JsonDict:
    fields = (
        "files_scanned",
        "functions_total",
        "cc_average",
        "max_cc",
        "high_complexity_functions",
        "mi_average",
        "import_edges",
        "public_defs",
        "all_exports",
    )
    return {
        field: round(float(current[field]) - float(baseline[field]), 2)
        for field in fields
    }


def _ensure_compatible_baseline(
    baseline: Mapping[str, Any],
    current: Mapping[str, Any],
) -> None:
    if baseline.get("schema_version") != current.get("schema_version"):
        raise ValueError("Complexity baseline schema version differs.")
    if baseline.get("paths") != current.get("paths"):
        raise ValueError("Complexity baseline paths differ.")
    if baseline.get("threshold") != current.get("threshold"):
        raise ValueError("Complexity baseline threshold differs.")


def _format_text(snapshot: Mapping[str, Any]) -> str:
    summary = snapshot["summary"]
    lines = [
        "Complexity measurement snapshot",
        f"schema_version: {snapshot['schema_version']}",
        f"paths: {', '.join(snapshot['paths'])}",
        f"threshold: {snapshot['threshold']}",
        "",
        "summary:",
        *_format_mapping(summary),
    ]
    if "delta_from_baseline" in snapshot:
        lines.extend(
            [
                "",
                "delta_from_baseline:",
                *_format_mapping(snapshot["delta_from_baseline"]),
            ]
        )
    lines.extend(["", "groups:"])
    for group, group_summary in snapshot["groups"].items():
        lines.append(f"  {group}:")
        lines.extend(f"    {line}" for line in _format_mapping(group_summary))
    lines.extend(["", "top high_complexity_functions:"])
    high = snapshot["high_complexity_functions"][:20]
    if not high:
        lines.append("  none")
    for item in high:
        lines.append(
            f"  {item['path']}:{item['lineno']}:{item['qualname']}: cc={item['cc']}"
        )
    return "\n".join(lines)


def _format_mapping(values: Mapping[str, Any]) -> list[str]:
    return [f"  {key}: {value}" for key, value in values.items()]


def _path_group(path: Path) -> str:
    rel = path.relative_to(ROOT)
    if rel.parts[0] in {"src", "tests", "scripts"}:
        return rel.parts[0]
    return "other"


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
