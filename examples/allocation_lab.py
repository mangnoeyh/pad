"""Create two deterministic allocation candidates from small synthetic inputs.

This teaching example permits unassigned items. Neither heuristic proves that a
full assignment is impossible, nor that its candidate is optimal. Compare saved
candidates with tools/check_allocations.py using their effective-input.json.

Limits: 4 MiB input, 1,000 resources, 10,000 items, 100,000 eligible edges,
and 128 characters per identifier. Only Python's standard library is used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any


MAX_INPUT_BYTES = 4 * 1024 * 1024
MAX_RESOURCES = 1_000
MAX_ITEMS = 10_000
MAX_EDGES = 100_000
MAX_ID_LENGTH = 128


def _fields(value: Any, expected: set[str], where: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{where} must contain exactly: {', '.join(sorted(expected))}")


def _identifier(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{where} must be a nonempty string without surrounding whitespace")
    if len(value) > MAX_ID_LENGTH:
        raise ValueError(f"{where} exceeds {MAX_ID_LENGTH} characters")
    if not value.isprintable():
        raise ValueError(f"{where} must contain only printable characters")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError(f"{where} must contain valid Unicode characters") from error
    return value


def _nonnegative_integer(value: Any, where: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{where} must be a nonnegative integer (booleans are not accepted)")
    return value


def validate_problem(raw: Any) -> dict[str, Any]:
    """Validate the schema and return a fresh copy without changing input order.

    A missing item/resource cost edge forbids that assignment. Each assigned item
    consumes one unit of capacity. Empty resource or item lists are supported.
    """
    _fields(raw, {"schema_version", "resources", "items"}, "input")
    if type(raw["schema_version"]) is not int or raw["schema_version"] != 1:
        raise ValueError("schema_version must be the integer 1")
    if not isinstance(raw["resources"], list) or len(raw["resources"]) > MAX_RESOURCES:
        raise ValueError(f"resources must be a list with at most {MAX_RESOURCES} entries")
    if not isinstance(raw["items"], list) or len(raw["items"]) > MAX_ITEMS:
        raise ValueError(f"items must be a list with at most {MAX_ITEMS} entries")

    resource_ids: set[str] = set()
    resources = []
    for index, entry in enumerate(raw["resources"]):
        where = f"resources[{index}]"
        _fields(entry, {"id", "capacity"}, where)
        resource_id = _identifier(entry["id"], f"{where}.id")
        if resource_id in resource_ids:
            raise ValueError(f"duplicate resource id: {resource_id!r}")
        resource_ids.add(resource_id)
        resources.append({
            "id": resource_id,
            "capacity": _nonnegative_integer(entry["capacity"], f"{where}.capacity"),
        })

    item_ids: set[str] = set()
    items = []
    edge_count = 0
    for index, entry in enumerate(raw["items"]):
        where = f"items[{index}]"
        _fields(entry, {"id", "costs"}, where)
        item_id = _identifier(entry["id"], f"{where}.id")
        if item_id in item_ids:
            raise ValueError(f"duplicate item id: {item_id!r}")
        item_ids.add(item_id)
        if not isinstance(entry["costs"], dict):
            raise ValueError(f"{where}.costs must be an object")
        edge_count += len(entry["costs"])
        if edge_count > MAX_EDGES:
            raise ValueError(f"input exceeds {MAX_EDGES} eligible cost edges")
        costs = {}
        for resource_id, cost in entry["costs"].items():
            if resource_id not in resource_ids:
                raise ValueError(f"{where}.costs refers to unknown resource: {resource_id!r}")
            costs[resource_id] = _nonnegative_integer(cost, f"{where}.costs[{resource_id!r}]")
        items.append({"id": item_id, "costs": costs})
    return {"schema_version": 1, "resources": resources, "items": items}


def build_candidates(problem: dict[str, Any]) -> dict[str, dict[str, str | None]]:
    """Return both heuristics, including partial or worse outcomes.

    Greedy visits items in input order. Scarcity visits the items with the fewest
    eligible resources of positive effective capacity first, breaking ties by
    item ID. That order is computed once. Both choose the cheapest resource with
    remaining capacity, breaking equal-cost ties by resource ID. Work is bounded
    by the input limits; there is no iterative search or optimality certificate.
    """
    problem = validate_problem(problem)
    capacities = {entry["id"]: entry["capacity"] for entry in problem["resources"]}
    items = problem["items"]

    def allocate(ordered_items: list[dict[str, Any]]) -> dict[str, str | None]:
        remaining = capacities.copy()
        assignment: dict[str, str | None] = {item["id"]: None for item in items}
        for item in ordered_items:
            available = (resource_id for resource_id in item["costs"] if remaining[resource_id] > 0)
            chosen = min(available, key=lambda resource_id: (item["costs"][resource_id], resource_id), default=None)
            if chosen is not None:
                assignment[item["id"]] = chosen
                remaining[chosen] -= 1
        return assignment

    scarcity_order = sorted(items, key=lambda item: (
        sum(capacities[resource_id] > 0 for resource_id in item["costs"]),
        item["id"],
    ))
    return {"greedy": allocate(items), "scarcity": allocate(scarcity_order)}


def _local_path(value: str | Path) -> Path:
    def check(raw: str) -> None:
        if raw.startswith(("//", "\\\\")) or "://" in raw or re.match(r"^[A-Za-z][A-Za-z0-9+.-]+:", raw):
            raise ValueError("only local filesystem paths are supported; URLs and network shares are rejected")

    check(str(value))
    resolved = Path(value).resolve()
    check(str(resolved))
    return resolved


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is not accepted: {value}")


def load_problem(path: Path) -> dict[str, Any]:
    """Read a bounded UTF-8 JSON file, including duplicate-key detection."""
    path = _local_path(path)
    if not path.is_file():
        raise ValueError(f"input must be a regular file: {path}")
    with path.open("rb") as handle:
        content = handle.read(MAX_INPUT_BYTES + 1)
    if len(content) > MAX_INPUT_BYTES:
        raise ValueError(f"input exceeds {MAX_INPUT_BYTES} bytes (4 MiB)")
    try:
        raw = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except RecursionError as error:
        raise ValueError("input JSON nesting is too deep") from error
    return validate_problem(raw)


def apply_capacities(problem: dict[str, Any], overrides: list[str]) -> dict[str, Any]:
    """Apply explicit operator settings to a validated copy, preserving source data."""
    effective = validate_problem(problem)
    resources = {entry["id"]: entry for entry in effective["resources"]}
    seen: set[str] = set()
    for override in overrides:
        resource_id, separator, capacity_text = override.rpartition("=")
        if not separator or not re.fullmatch(r"[0-9]+", capacity_text):
            raise ValueError(f"invalid --capacity {override!r}; expected RESOURCE_ID=NONNEGATIVE_INTEGER")
        if resource_id not in resources:
            raise ValueError(f"--capacity refers to unknown resource: {resource_id!r}")
        if resource_id in seen:
            raise ValueError(f"duplicate --capacity override for {resource_id!r}")
        seen.add(resource_id)
        resources[resource_id]["capacity"] = int(capacity_text)
    return effective


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def write_candidates(problem: dict[str, Any], output_dir: Path) -> Path:
    """Write an effective input and both candidates to a newly created directory."""
    requested_output = output_dir
    output_dir = _local_path(output_dir)
    if os.path.lexists(requested_output) or output_dir.exists():
        raise ValueError(f"refusing to overwrite existing output path: {output_dir}")
    problem = validate_problem(problem)
    effective_bytes = _json_bytes(problem)
    if len(effective_bytes) > MAX_INPUT_BYTES:
        raise ValueError(f"formatted effective input exceeds {MAX_INPUT_BYTES} bytes; reduce input size")
    digest = hashlib.sha256(effective_bytes).hexdigest()
    files = {"effective-input.json": effective_bytes}
    for method, assignment in build_candidates(problem).items():
        files[f"{method}.json"] = _json_bytes({
            "schema_version": 1,
            "method": method,
            "input_sha256": digest,
            "assignment": assignment,
        })
    # Reserve the destination before writing; exclusive file creation also avoids
    # replacing a file another process might create after directory creation.
    output_dir.mkdir(parents=True, exist_ok=False)
    for filename, content in files.items():
        with (output_dir / filename).open("xb") as handle:
            handle.write(content)
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Outputs are unverified candidates. Use tools/check_allocations.py with effective-input.json. Choose a new output directory for every run.",
    )
    parser.add_argument("--input", required=True, type=Path, help="local UTF-8 problem JSON")
    parser.add_argument("--output-dir", required=True, type=Path, help="new directory; existing paths are rejected")
    parser.add_argument("--capacity", action="append", default=[], metavar="RESOURCE_ID=N", help="override one capacity; repeat for different resources")
    args = parser.parse_args()
    try:
        problem = apply_capacities(load_problem(args.input), args.capacity)
        destination = write_candidates(problem, args.output_dir)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(2, f"error: {error}\n")
    print(f"Saved effective-input.json, greedy.json and scarcity.json in {destination}")
    print("Candidates require independent verification; no optimality claim is made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
