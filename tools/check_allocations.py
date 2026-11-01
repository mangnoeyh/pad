"""Independent checks for the synthetic single-choice capacity teaching example.

This is deliberately one small contract, not a checker for arbitrary optimization
tasks. It never imports the candidate generator or trusts its claimed result.
The exact reference enumerates a bounded Cartesian product independently.
"""

import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import sys


CONTRACT_ID = "single-choice-capacity-v1"
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_RESOURCES = 1000
MAX_ITEMS = 10000
MAX_EDGES = 100000
MAX_ID_LENGTH = 128
DEFAULT_ORACLE_LIMIT = 200000
HARD_ORACLE_LIMIT = 1000000
MAX_ORACLE_ITEMS = 200
OBJECTIVE_ORDER = [
    {"metric": "assigned_count", "direction": "maximize"},
    {"metric": "total_cost", "direction": "minimize"},
]


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _constant(value):
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def _local_path(path):
    path = Path(path)
    for value in (str(path), str(path.resolve())):
        if (value.startswith(("//", "\\\\")) or "://" in value
                or re.match(r"^[A-Za-z][A-Za-z0-9+.-]+:", value)):
            raise ValueError("only local filesystem paths are supported")
    return path.resolve()


def read_json(path):
    """Return (decoded JSON, sha256 of exact bytes); reject ambiguous JSON."""
    path = _local_path(path)
    if not path.is_file():
        raise OSError(f"JSON input must be a regular file: {path}")
    with path.open("rb") as stream:
        raw = stream.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError(f"JSON file exceeds {MAX_FILE_BYTES} bytes")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_object,
                          parse_constant=_constant)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError(f"invalid JSON encoding or nesting: {exc}") from exc
    return data, hashlib.sha256(raw).hexdigest()


def _fields(data, expected, label):
    if not isinstance(data, dict):
        raise ValueError(f"{label} must be an object")
    if set(data) != set(expected):
        raise ValueError(f"{label} requires exactly these fields: {', '.join(expected)}")


def _identifier(value, label):
    if (not isinstance(value, str) or not value or len(value) > MAX_ID_LENGTH
            or value.strip() != value or not value.isprintable()):
        raise ValueError(f"{label} must be a nonempty printable ID of at most "
                         f"{MAX_ID_LENGTH} characters without surrounding whitespace")
    return value


def _nonnegative_integer(value, label):
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer (not boolean)")
    return value


def validate_problem(data):
    """Validate the exact v1 input schema and return a detached, ordered copy.

    Capacity is a count of items; costs are nonnegative integer teaching units.
    Missing edges are forbidden. Null assignment is always permitted, including
    for inputs with zero resources or zero items.
    """
    _fields(data, ("schema_version", "resources", "items"), "input")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError("input schema_version must be integer 1")
    resources, items = data["resources"], data["items"]
    if not isinstance(resources, list) or len(resources) > MAX_RESOURCES:
        raise ValueError(f"resources must be a list of at most {MAX_RESOURCES} entries")
    if not isinstance(items, list) or len(items) > MAX_ITEMS:
        raise ValueError(f"items must be a list of at most {MAX_ITEMS} entries")
    resource_ids, checked_resources = set(), []
    for row in resources:
        _fields(row, ("id", "capacity"), "resource")
        rid = _identifier(row["id"], "resource id")
        if rid in resource_ids:
            raise ValueError(f"duplicate resource id: {rid!r}")
        capacity = _nonnegative_integer(row["capacity"], f"capacity of {rid!r}")
        resource_ids.add(rid)
        checked_resources.append({"id": rid, "capacity": capacity})
    item_ids, checked_items, edges = set(), [], 0
    for row in items:
        _fields(row, ("id", "costs"), "item")
        iid = _identifier(row["id"], "item id")
        if iid in item_ids:
            raise ValueError(f"duplicate item id: {iid!r}")
        if not isinstance(row["costs"], dict):
            raise ValueError(f"costs of {iid!r} must be an object")
        costs = {}
        for rid, cost in row["costs"].items():
            _identifier(rid, "cost resource id")
            if rid not in resource_ids:
                raise ValueError(f"unknown resource {rid!r} in costs of {iid!r}")
            costs[rid] = _nonnegative_integer(cost, f"cost of {iid!r} on {rid!r}")
        edges += len(costs)
        if edges > MAX_EDGES:
            raise ValueError(f"input exceeds {MAX_EDGES} allowed edges")
        item_ids.add(iid)
        checked_items.append({"id": iid, "costs": costs})
    return {"schema_version": 1, "resources": checked_resources, "items": checked_items}


def _objective(assigned_count, total_cost):
    return {"assigned_count": assigned_count, "total_cost": total_cost}


def _rank(objective):
    return (-objective["assigned_count"], objective["total_cost"])


def check_candidate(problem, candidate, input_sha256, source=None):
    """Recompute an assignment; invalid candidates have no comparable objective.

    For malformed candidates, metrics count only individually permitted edges.
    Such partial diagnostic metrics are not a feasibility or quality claim.
    """
    problem = validate_problem(problem)
    if (not isinstance(input_sha256, str) or len(input_sha256) != 64
            or any(c not in "0123456789abcdef" for c in input_sha256)):
        raise ValueError("input_sha256 must be the lowercase SHA-256 of the input bytes")
    violations = []

    def flag(code, message):
        violations.append({"code": code, "message": message})

    if not isinstance(candidate, dict):
        flag("candidate_type", "candidate must be an object")
        candidate = {}
    fields = {"schema_version", "method", "input_sha256", "assignment"}
    if set(candidate) != fields:
        flag("candidate_fields", "candidate requires exactly schema_version, method, "
             "input_sha256, assignment")
    if type(candidate.get("schema_version")) is not int or candidate.get("schema_version") != 1:
        flag("schema_version", "candidate schema_version must be integer 1")
    method = candidate.get("method")
    if not isinstance(method, str) or method not in ("greedy", "scarcity"):
        flag("method", "candidate method must be greedy or scarcity")
    if candidate.get("input_sha256") != input_sha256:
        flag("input_hash_mismatch", "candidate does not match the exact saved input bytes")
    assignment = candidate.get("assignment")
    if not isinstance(assignment, dict):
        flag("assignment_type", "assignment must be an object")
        assignment = {}
    item_ids = {item["id"] for item in problem["items"]}
    missing = sorted(item_ids - set(assignment))
    extra = sorted(set(assignment) - item_ids, key=str)
    if missing:
        flag("missing_item_ids", f"missing assignment IDs: {missing!r}")
    if extra:
        flag("extra_item_ids", f"unknown assignment IDs: {extra!r}")
    capacities = {row["id"]: row["capacity"] for row in problem["resources"]}
    load = dict.fromkeys(capacities, 0)
    assigned_count, total_cost, unassigned = 0, 0, []
    for item in problem["items"]:
        iid = item["id"]
        selected = assignment.get(iid)
        if selected is None:
            unassigned.append(iid)
            continue
        if not isinstance(selected, str):
            flag("assignment_value_type", f"assignment of {iid!r} must be a resource ID or null")
            unassigned.append(iid)
            continue
        if selected not in capacities:
            flag("unknown_resource", f"assignment of {iid!r} names unknown resource {selected!r}")
            unassigned.append(iid)
            continue
        if selected not in item["costs"]:
            flag("forbidden_resource", f"item {iid!r} has no allowed edge to {selected!r}")
            unassigned.append(iid)
            continue
        assigned_count += 1
        total_cost += item["costs"][selected]
        load[selected] += 1
    for rid, used in load.items():
        if used > capacities[rid]:
            flag("over_capacity", f"resource {rid!r} uses {used} slots; capacity is {capacities[rid]}")
    valid = not violations
    complete = valid and assigned_count == len(problem["items"])
    return {
        "source": str(source) if source is not None else None,
        "method": method,
        "valid": valid,
        "completeness": ("complete" if complete else "partial") if valid else "invalid",
        "complete": complete,
        "violations": violations,
        "coverage": {"item_count": len(item_ids), "assignment_key_count": len(assignment),
                     "missing_item_ids": missing, "extra_item_ids": extra},
        "metrics": {"assigned_count": assigned_count, "unassigned_count": len(unassigned),
                    "unassigned_item_ids": unassigned, "total_cost": total_cost,
                    "resource_load": load},
        "objective": _objective(assigned_count, total_cost) if valid else None,
    }


def exact_reference(problem, limit=DEFAULT_ORACLE_LIMIT):
    """Exhaustively enumerate tiny inputs; skipped never means optimal/infeasible.

    The product includes each allowed resource and null for every item, without
    calling the candidate checker or solver to compute feasibility or objective.
    """
    problem = validate_problem(problem)
    if type(limit) is not int or limit < 1:
        raise ValueError("oracle limit must be a positive integer")
    effective_limit = min(limit, HARD_ORACLE_LIMIT)
    result = {"status": "skipped", "reason": None, "requested_limit": limit,
              "effective_limit": effective_limit, "hard_limit": HARD_ORACLE_LIMIT,
              "item_limit": MAX_ORACLE_ITEMS, "states_examined": 0,
              "objective": None, "assignment": None, "complete": None}
    items = problem["items"]
    if len(items) > MAX_ORACLE_ITEMS:
        result.update(reason="item_limit_exceeded", combinations=None)
        return result
    combinations = 1
    for item in items:
        combinations *= len(item["costs"]) + 1
    result["combinations"] = combinations
    if combinations > effective_limit:
        result["reason"] = "combination_limit_exceeded"
        return result
    capacities = {row["id"]: row["capacity"] for row in problem["resources"]}
    options = [tuple(sorted(item["costs"])) + (None,) for item in items]
    best_key, best_values = None, None
    feasible_states = 0
    for chosen in itertools.product(*options):
        result["states_examined"] += 1
        counts, assigned_count, cost, feasible = {}, 0, 0, True
        for item, resource in zip(items, chosen):
            if resource is None:
                continue
            counts[resource] = counts.get(resource, 0) + 1
            if counts[resource] > capacities[resource]:
                feasible = False
                break
            assigned_count += 1
            cost += item["costs"][resource]
        if not feasible:
            continue
        feasible_states += 1
        key = (-assigned_count, cost)
        if best_key is None or key < best_key:
            best_key, best_values = key, chosen
    # At least the all-null assignment is feasible, even with empty input.
    result.update(status="completed", reason=None, feasible_states=feasible_states,
                  objective=_objective(-best_key[0], best_key[1]),
                  assignment={item["id"]: value for item, value in zip(items, best_values)},
                  complete=-best_key[0] == len(items))
    return result


def _positive_limit(value):
    try:
        limit = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("oracle limit must be a positive integer") from exc
    if limit < 1:
        raise argparse.ArgumentTypeError("oracle limit must be a positive integer")
    return limit


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--candidates", required=True, nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path, help="new JSON report path; never overwritten")
    parser.add_argument("--oracle-limit", type=_positive_limit, default=DEFAULT_ORACLE_LIMIT)
    parser.add_argument("--no-oracle", action="store_true")
    args = parser.parse_args(argv)
    try:
        if os.path.lexists(args.output):
            raise FileExistsError(f"output already exists: {args.output}")
        args.output = _local_path(args.output)
        if args.output.exists():
            raise FileExistsError(f"output already exists: {args.output}")
        raw_problem, input_hash = read_json(args.input)
        problem = validate_problem(raw_problem)
        evaluations = []
        for path in args.candidates:
            try:
                candidate, _ = read_json(path)
            except ValueError as exc:
                evaluation = check_candidate(problem, {}, input_hash, path)
                evaluation["violations"] = [{"code": "candidate_json", "message": str(exc)}]
            else:
                evaluation = check_candidate(problem, candidate, input_hash, path)
            evaluations.append(evaluation)
        valid = [entry for entry in evaluations if entry["valid"]]
        best_objective = min((entry["objective"] for entry in valid), key=_rank) if valid else None
        best_candidates = [entry["source"] for entry in valid if entry["objective"] == best_objective]
        oracle = ({"status": "skipped", "reason": "disabled", "objective": None,
                   "assignment": None, "states_examined": 0, "complete": None}
                  if args.no_oracle else exact_reference(problem, args.oracle_limit))
        for entry in evaluations:
            entry["matches_oracle"] = (entry["objective"] == oracle["objective"]
                                       if entry["valid"] and oracle["status"] == "completed" else None)
        report = {
            "schema_version": 1, "contract_id": CONTRACT_ID,
            "scope": "Synthetic teaching example only; capacities count items and costs use integer units.",
            "input_sha256": input_hash, "objective_order": OBJECTIVE_ORDER,
            "input_summary": {"item_count": len(problem["items"]),
                              "resource_count": len(problem["resources"])},
            "all_candidates_valid": all(entry["valid"] for entry in evaluations),
            "candidates": evaluations, "best_candidates": best_candidates,
            "best_objective": best_objective, "oracle": oracle,
            "notes": ["Null assignments are allowed and reported as partial when items remain unassigned.",
                      "Invalid candidates are excluded; their metrics count only individually permitted edges.",
                      "Oracle completion proves the objective only for this saved input and fixed teaching contract.",
                      "A skipped oracle supplies no optimality or infeasibility conclusion."],
        }
        encoded = json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False) + "\n"
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(encoded)
    except (OSError, ValueError, RecursionError) as exc:
        print(f"check_allocations: {exc}", file=sys.stderr)
        return 2
    print(f"Wrote {args.output}; valid candidates: {len(valid)}/{len(evaluations)}; "
          f"oracle: {oracle['status']}")
    return 0 if report["all_candidates_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
