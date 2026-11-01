"""Bounded first-improvement reversal for a fixed directed closed tour."""

from ._validation import integer, sequence, vertex


def improve_tour(costs, tour, *, max_evaluations=10_000):
    """Keep the first vertex fixed; recompute complete directed costs per move.

    This models no capacities, time windows, omitted stops or choice of stops.
    local_optimum means only no improving segment reversal, not global optimality.
    """
    sequence(costs, "costs")
    sequence(tour, "tour")
    integer(max_evaluations, "max_evaluations", 1, 1_000_000)
    n = len(costs)
    for row in costs:
        sequence(row, "cost row")
        if len(row) != n:
            raise ValueError("costs must be square")
        for value in row:
            integer(value, "cost", 0)
    clean = [vertex(v, n) for v in tour]
    if len(clean) != n or len(set(clean)) != n:
        raise ValueError("tour must be a permutation of all matrix indices")

    def cost(route):
        if len(route) < 2:
            return 0
        return sum(costs[route[i]][route[(i + 1) % n]] for i in range(n))

    current = cost(clean)
    initial, evaluations, accepted = current, 0, 0
    while True:
        improved = False
        for start in range(1, n - 1):
            for end in range(start + 1, n):
                if evaluations == max_evaluations:
                    return {"tour": clean, "initial_cost": initial, "cost": current,
                            "evaluations": evaluations, "accepted": accepted,
                            "stop_reason": "evaluation_limit", "global_optimality_proven": False}
                proposed = clean[:start] + list(reversed(clean[start:end + 1])) + clean[end + 1:]
                value = cost(proposed)
                evaluations += 1
                if value < current:
                    clean, current, improved = proposed, value, True
                    accepted += 1
                    break
            if improved:
                break
        if not improved:
            return {"tour": clean, "initial_cost": initial, "cost": current,
                    "evaluations": evaluations, "accepted": accepted,
                    "stop_reason": "local_optimum", "global_optimality_proven": False}
