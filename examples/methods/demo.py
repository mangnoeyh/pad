"""Print small synthetic results; no downloads or filesystem writes."""

import json

from .allocation import bipartite_matching, exact_capacitated_assignment, maximum_flow
from .graphs import bfs, dijkstra, minimum_spanning_forest, topological_sort
from .local_search import improve_tour
from .sequences import Fenwick, knapsack_01, merge_intervals, prefix_sums, sliding_maximum, weighted_interval_schedule


def main():
    tree = Fenwick([3, -1, 4])
    tree.add(1, 2)
    costs = [[0, 9, 1, 5], [2, 0, 8, 1], [3, 1, 0, 7], [1, 4, 2, 0]]
    result = {
        "scope": "synthetic function examples; no service or real input validation claimed",
        "bfs": bfs(4, [(0, 1), (1, 2)], 0),
        "dijkstra": dijkstra(4, [(0, 1, 4), (0, 2, 1), (2, 1, 1)], 0),
        "topological_sort": topological_sort(4, [(0, 2), (1, 2), (2, 3)]),
        "minimum_spanning_forest": minimum_spanning_forest(4, [(0, 1, 3), (1, 2, 1), (0, 2, 2)]),
        "prefix_sums": prefix_sums([3, -1, 4]),
        "fenwick_after_update": tree.range_sum(0, 3),
        "sliding_maximum": sliding_maximum([2, 1, 4, 3], 2),
        "merge_intervals": merge_intervals([(0, 3), (2, 4), (4, 5)]),
        "weighted_interval_schedule": weighted_interval_schedule([(0, 3, 5), (3, 5, 4), (0, 5, 8)]),
        "knapsack_01": knapsack_01([(2, 4), (3, 5), (4, 7)], 5),
        "bipartite_matching": bipartite_matching([[0, 1], [0]], 2),
        "maximum_flow": maximum_flow(4, [(0, 1, 2), (0, 2, 1), (1, 3, 2), (2, 3, 1)], 0, 3),
        "exact_capacitated_assignment": exact_capacitated_assignment([[1, 2], [1, None]], [1, 1]),
        "directed_tour_improvement": improve_tour(costs, [0, 1, 2, 3]),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
