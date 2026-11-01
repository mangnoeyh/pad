"""Unit-demand matching, single-commodity flow and a bounded exact reference."""

from collections import deque
from itertools import product

from ._validation import edge_list, integer, sequence, vertex


def bipartite_matching(adjacency, right_count):
    """Maximum-cardinality one-to-one matching; no costs or group constraints."""
    sequence(adjacency, "adjacency")
    integer(right_count, "right_count", 0)
    clean = []
    for neighbors in adjacency:
        sequence(neighbors, "neighbors")
        clean.append(sorted({vertex(v, right_count) for v in neighbors}))
    left_match, right_match = [None] * len(clean), [None] * right_count
    for root in range(len(clean)):
        queue, visited_left, previous_right = deque([root]), {root}, {}
        free = None
        while queue and free is None:
            left = queue.popleft()
            for right in clean[left]:
                if right in previous_right:
                    continue
                previous_right[right] = left
                matched = right_match[right]
                if matched is None:
                    free = right
                    break
                if matched not in visited_left:
                    visited_left.add(matched)
                    queue.append(matched)
        while free is not None:
            left = previous_right[free]
            old = left_match[left]
            left_match[left], right_match[free] = free, left
            free = old
    return {"assignment": left_match, "matched": sum(v is not None for v in left_match)}


def maximum_flow(node_count, edges, source, sink):
    """Edmonds-Karp with sparse residual maps and a minimum-cut certificate."""
    edges = edge_list(node_count, edges, weighted=True, nonnegative=True)
    vertex(source, node_count, "source")
    vertex(sink, node_count, "sink")
    if source == sink:
        raise ValueError("source and sink must differ")
    capacity = {}
    residual = [{} for _ in range(node_count)]
    for u, v, amount in edges:
        capacity[u, v] = capacity.get((u, v), 0) + amount
        residual[u][v] = residual[u].get(v, 0) + amount
        residual[v].setdefault(u, 0)
    neighbors = [sorted(row) for row in residual]
    total = 0
    while True:
        previous = {source: None}
        queue = deque([source])
        while queue and sink not in previous:
            u = queue.popleft()
            for v in neighbors[u]:
                if v not in previous and residual[u][v] > 0:
                    previous[v] = u
                    queue.append(v)
        if sink not in previous:
            reachable = set(previous)
            break
        path, cursor = [], sink
        while cursor != source:
            before = previous[cursor]
            path.append((before, cursor))
            cursor = before
        amount = min(residual[u][v] for u, v in path)
        for u, v in path:
            residual[u][v] -= amount
            residual[v][u] = residual[v].get(u, 0) + amount
        total += amount
    flows = [(u, v, max(0, amount - residual[u][v])) for (u, v), amount in sorted(capacity.items())]
    cut_capacity = sum(amount for (u, v), amount in capacity.items() if u in reachable and v not in reachable)
    return {"value": total, "flows": flows, "source_side": sorted(reachable), "cut_capacity": cut_capacity}


def exact_capacitated_assignment(costs, capacities, *, max_states=200_000):
    """Enumerate a tiny fixed model: maximize assigned count, then minimize cost.

    None means a forbidden edge. Explicitly skipped searches have no objective
    or assignment; an exhausted search may return a valid partial assignment.
    """
    sequence(costs, "costs")
    sequence(capacities, "capacities")
    integer(max_states, "max_states", 1, 1_000_000)
    capacity = [integer(v, "capacity", 0) for v in capacities]
    choices = []
    states = 1
    for row in costs:
        sequence(row, "cost row")
        if len(row) != len(capacity):
            raise ValueError("every cost row must match capacities")
        for cost in row:
            if cost is not None:
                integer(cost, "cost", 0)
        allowed = [i for i, value in enumerate(row) if value is not None and capacity[i] > 0]
        choices.append(allowed + [None])
        states *= len(allowed) + 1
    skipped = {"status": "skipped", "states": states, "objective": None, "assignment": None}
    if len(costs) > 200:
        return dict(skipped, reason="item_limit")
    if states > max_states:
        return dict(skipped, reason="state_limit")
    best_key, best_assignment = None, None
    for assignment in product(*choices):
        loads = [0] * len(capacity)
        assigned, total_cost, valid = 0, 0, True
        for index, resource in enumerate(assignment):
            if resource is None:
                continue
            loads[resource] += 1
            if loads[resource] > capacity[resource]:
                valid = False
                break
            assigned += 1
            total_cost += costs[index][resource]
        if valid:
            key = (-assigned, total_cost)
            if best_key is None or key < best_key:
                best_key, best_assignment = key, list(assignment)
    return {"status": "optimal", "states": states,
            "objective": {"assigned": -best_key[0], "cost": best_key[1]},
            "assignment": best_assignment, "complete": -best_key[0] == len(costs)}
