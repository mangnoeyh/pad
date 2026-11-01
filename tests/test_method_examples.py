"""Small exhaustive references and invariant checks for independent examples."""

from copy import deepcopy
from itertools import combinations, permutations, product
import json
from pathlib import Path
import random
import subprocess
import sys
import unittest
from unittest.mock import patch

from examples.methods.allocation import bipartite_matching, exact_capacitated_assignment, maximum_flow
from examples.methods.graphs import DisjointSet, bfs, dijkstra, minimum_spanning_forest, topological_sort
from examples.methods.local_search import improve_tour
from examples.methods.sequences import Fenwick, knapsack_01, merge_intervals, prefix_sums, sliding_maximum, weighted_interval_schedule


def simple_path_distances(n, edges, source):
    """Enumerate simple paths, independent of heap/frontier shortest-path logic."""
    answer = [None] * n
    answer[source] = 0
    for length in range(1, n):
        for suffix in permutations([v for v in range(n) if v != source], length):
            route = (source,) + suffix
            total = 0
            for u, v in zip(route, route[1:]):
                choices = [w for a, b, w in edges if (a, b) == (u, v)]
                if not choices:
                    break
                total += min(choices)
            else:
                end = route[-1]
                if answer[end] is None or total < answer[end]:
                    answer[end] = total
    return answer


def partition_assignment_reference(costs, capacities):
    """DP over resource load states, independent of product enumeration."""
    states = {(0,) * len(capacities): (0, 0)}
    for row in costs:
        following = dict(states)
        for loads, (count, cost) in states.items():
            for resource, edge in enumerate(row):
                if edge is None or loads[resource] >= capacities[resource]:
                    continue
                new_loads = list(loads)
                new_loads[resource] += 1
                key = tuple(new_loads)
                proposed = count + 1, cost + edge
                old = following.get(key)
                if old is None or (-proposed[0], proposed[1]) < (-old[0], old[1]):
                    following[key] = proposed
        states = following
    return min(states.values(), key=lambda value: (-value[0], value[1]))


class GraphExamplesTests(unittest.TestCase):
    def test_bfs_direction_parallel_and_disconnected(self):
        edges = [(0, 1), (0, 1), (1, 2), (2, 2)]
        self.assertEqual(bfs(4, edges, 2, directed=True)[0], [None, None, 0, None])
        self.assertEqual(bfs(4, edges, 2)[0], [2, 1, 0, None])

    def test_shortest_paths_against_exhaustive_paths(self):
        rng = random.Random(121)
        for trial in range(35):
            n = rng.randint(1, 5)
            edges = [(u, v, rng.randint(0, 9)) for u in range(n) for v in range(n) if rng.random() < .3]
            source = rng.randrange(n)
            with self.subTest(trial=trial):
                distance, parent = dijkstra(n, edges, source)
                self.assertEqual(distance, simple_path_distances(n, edges, source))
                for v, before in enumerate(parent):
                    if before is not None:
                        self.assertTrue(any(u == before and end == v and distance[u] + w == distance[v] for u, end, w in edges))
                unweighted = [(u, v) for u, v, _ in edges]
                self.assertEqual(bfs(n, unweighted, source, directed=True)[0],
                                 simple_path_distances(n, [(u, v, 1) for u, v in unweighted], source))

    def test_dijkstra_zero_cost_cycle_and_parallel_edges(self):
        distance, parent = dijkstra(4, [(0, 1, 9), (0, 1, 0), (1, 0, 0), (1, 2, 2)], 0)
        self.assertEqual(distance, [0, 0, 2, None])
        self.assertIsNone(parent[0])

    def test_topological_order_matches_enumerated_orders(self):
        rng = random.Random(122)
        for n in range(6):
            edges = [(u, v) for u in range(n) for v in range(u + 1, n) if rng.random() < .5]
            orders = [p for p in permutations(range(n)) if all(p.index(u) < p.index(v) for u, v in edges)]
            self.assertEqual(topological_sort(n, edges + edges), list(min(orders)))

    def test_topological_cycle_and_self_loop_fail(self):
        for edges in ([(0, 1), (1, 0)], [(1, 1)]):
            with self.assertRaisesRegex(ValueError, "cycle"):
                topological_sort(2, edges)

    def test_dsu_repeated_union_and_empty(self):
        ds = DisjointSet(5)
        for a, b in [(0, 1), (2, 3), (1, 3), (0, 3)]:
            ds.union(a, b)
        self.assertEqual(ds.components, 2)
        self.assertEqual(len({ds.find(i) for i in range(4)}), 1)
        self.assertNotEqual(ds.find(0), ds.find(4))
        with self.assertRaises(ValueError):
            DisjointSet(0).find(0)

    def test_mst_against_enumerated_trees(self):
        rng = random.Random(123)
        for trial in range(30):
            n = rng.randint(2, 5)
            edges = [(i, i + 1, rng.randint(-3, 8)) for i in range(n - 1)]
            edges += [(u, v, rng.randint(-3, 8)) for u in range(n) for v in range(u + 2, n) if rng.random() < .5]
            candidates = []
            for subset in combinations(edges, n - 1):
                reached = {0}
                while True:
                    expanded = reached | {v for u, v, _ in subset if u in reached} | {u for u, v, _ in subset if v in reached}
                    if reached == expanded:
                        break
                    reached = expanded
                if len(reached) == n:
                    candidates.append(sum(w for _, _, w in subset))
            result = minimum_spanning_forest(n, edges)
            with self.subTest(trial=trial):
                self.assertEqual(result["total_cost"], min(candidates))
                self.assertEqual(result["components"], 1)
                self.assertEqual(len(result["edges"]), n - 1)

    def test_forest_is_not_reported_as_connected(self):
        result = minimum_spanning_forest(5, [(0, 1, 3), (0, 1, 1), (2, 3, -2), (4, 4, -99)])
        self.assertEqual(result, {"edges": [(2, 3, -2), (0, 1, 1)], "total_cost": -1, "components": 3})
        self.assertEqual(minimum_spanning_forest(0, [])["components"], 0)

    def test_graph_input_validation(self):
        invalid = [lambda: bfs(True, [], 0), lambda: bfs(0, [], 0),
                   lambda: bfs(2, [(0, 2)], 0), lambda: bfs(2, [(0, 1)], 0, directed=1),
                   lambda: dijkstra(2, [(0, 1, -1)], 0), lambda: dijkstra(2, [(0, 1, True)], 0),
                   lambda: dijkstra(2, [(0, 1, 1.5)], 0), lambda: topological_sort(2, [(0,)]),
                   lambda: minimum_spanning_forest(2, [(0, 1, False)])]
        for operation in invalid:
            with self.assertRaises(ValueError):
                operation()


class SequenceExamplesTests(unittest.TestCase):
    def test_prefix_and_fenwick_match_mutable_model(self):
        rng = random.Random(201)
        for n in range(10):
            values = [rng.randint(-10, 10) for _ in range(n)]
            self.assertEqual(prefix_sums(values), [sum(values[:i]) for i in range(n + 1)])
            tree = Fenwick(values)
            for _ in range(20):
                if n:
                    index, delta = rng.randrange(n), rng.randint(-4, 4)
                    values[index] += delta
                    tree.add(index, delta)
                for left in range(n + 1):
                    for right in range(left, n + 1):
                        self.assertEqual(tree.range_sum(left, right), sum(values[left:right]))

    def test_window_maximum_against_slicing(self):
        rng = random.Random(202)
        for n in range(20):
            values = [rng.randint(-3, 3) for _ in range(n)]
            for width in range(1, n + 3):
                expected = [max(values[i:i + width]) for i in range(n - width + 1)]
                self.assertEqual(sliding_maximum(values, width), expected)

    def test_interval_merge_boundaries_and_coverage(self):
        self.assertEqual(merge_intervals([(0, 2), (2, 4)]), [(0, 2), (2, 4)])
        self.assertEqual(merge_intervals([(0, 2), (2, 4)], merge_touching=True), [(0, 4)])
        rng = random.Random(203)
        for _ in range(40):
            rows = [(a, a + rng.randint(1, 5)) for a in [rng.randint(-4, 8) for _ in range(8)]]
            merged = merge_intervals(rows)
            covered = {i for a, b in rows for i in range(a, b)}
            self.assertEqual(covered, {i for a, b in merged for i in range(a, b)})
            self.assertTrue(all(b <= c for (a, b), (c, d) in zip(merged, merged[1:])))

    def test_weighted_schedule_against_all_subsets(self):
        rng = random.Random(204)
        for trial in range(50):
            rows = [(a, a + rng.randint(1, 4), rng.randint(0, 9)) for a in [rng.randint(-2, 6) for _ in range(rng.randint(0, 8))]]
            best = 0
            for mask in range(1 << len(rows)):
                chosen = sorted(rows[i] for i in range(len(rows)) if mask >> i & 1)
                if all(b <= c for (a, b, _), (c, d, _) in zip(chosen, chosen[1:])):
                    best = max(best, sum(row[2] for row in chosen))
            result = weighted_interval_schedule(rows)
            selected = [rows[i] for i in result["indices"]]
            with self.subTest(trial=trial):
                self.assertEqual(result["value"], best)
                self.assertEqual(sum(row[2] for row in selected), best)
                self.assertTrue(all(a[1] <= b[0] for a, b in zip(selected, selected[1:])))

    def test_knapsack_against_all_subsets(self):
        rng = random.Random(205)
        for trial in range(60):
            rows = [(rng.randint(1, 7), rng.randint(0, 12)) for _ in range(rng.randint(0, 8))]
            capacity = rng.randint(0, 15)
            feasible = [(sum(v for i, (w, v) in enumerate(rows) if mask >> i & 1),
                         sum(w for i, (w, v) in enumerate(rows) if mask >> i & 1))
                        for mask in range(1 << len(rows))]
            expected = max(value for value, weight in feasible if weight <= capacity)
            result = knapsack_01(rows, capacity)
            with self.subTest(trial=trial):
                self.assertEqual(result["value"], expected)
                self.assertEqual(sum(rows[i][0] for i in result["indices"]), result["weight"])
                self.assertEqual(sum(rows[i][1] for i in result["indices"]), expected)
                self.assertLessEqual(result["weight"], capacity)
                self.assertEqual(len(result["indices"]), len(set(result["indices"])))

    def test_knapsack_preallocation_budget(self):
        with self.assertRaisesRegex(ValueError, "budget"):
            knapsack_01([(1, 1)], 10**12)
        with self.assertRaises(ValueError):
            knapsack_01([], 0, max_cells=10_000_001)

    def test_sequence_input_validation(self):
        invalid = [lambda: prefix_sums([True]), lambda: Fenwick([1.0]),
                   lambda: Fenwick([]).add(0, 1), lambda: Fenwick([1]).range_sum(1, 0),
                   lambda: Fenwick([1]).prefix(2), lambda: sliding_maximum([1], 0),
                   lambda: merge_intervals([(2, 2)]), lambda: merge_intervals([(0, 1)], merge_touching=1),
                   lambda: weighted_interval_schedule([(0, 1, -1)]),
                   lambda: knapsack_01([(0, 1)], 1), lambda: knapsack_01([(1, False)], 1)]
        for operation in invalid:
            with self.assertRaises(ValueError):
                operation()


class AllocationExamplesTests(unittest.TestCase):
    def test_matching_repairs_greedy_trap(self):
        self.assertEqual(bipartite_matching([[0, 1], [0]], 2), {"assignment": [1, 0], "matched": 2})
        self.assertEqual(bipartite_matching([[], []], 0), {"assignment": [None, None], "matched": 0})
        self.assertEqual(bipartite_matching([], 0)["matched"], 0)

    def test_matching_against_enumeration(self):
        rng = random.Random(301)
        for trial in range(60):
            left, right = rng.randint(0, 5), rng.randint(0, 4)
            rows = [[r for r in range(right) if rng.random() < .45] for _ in range(left)]
            expected = 0
            for candidate in product(*[row + [None] for row in rows]):
                assigned = [r for r in candidate if r is not None]
                if len(assigned) == len(set(assigned)):
                    expected = max(expected, len(assigned))
            result = bipartite_matching(rows, right)
            with self.subTest(trial=trial):
                self.assertEqual(result["matched"], expected)
                chosen = [v for v in result["assignment"] if v is not None]
                self.assertEqual(len(chosen), len(set(chosen)))
                self.assertTrue(all(v is None or v in rows[i] for i, v in enumerate(result["assignment"])))

    def test_flow_against_all_cuts_and_conservation(self):
        rng = random.Random(302)
        for trial in range(50):
            n = rng.randint(2, 6)
            edges = [(u, v, rng.randint(0, 5)) for u in range(n) for v in range(n) if rng.random() < .3]
            if edges:
                edges.append(edges[0])
            cuts = []
            for mask in range(1 << (n - 2)):
                source_side = {0} | {v for v in range(1, n - 1) if mask >> (v - 1) & 1}
                cuts.append(sum(c for u, v, c in edges if u in source_side and v not in source_side))
            result = maximum_flow(n, edges, 0, n - 1)
            balance = [0] * n
            capacity = {}
            for u, v, value in edges:
                capacity[u, v] = capacity.get((u, v), 0) + value
            for u, v, value in result["flows"]:
                self.assertGreaterEqual(value, 0)
                self.assertLessEqual(value, capacity[u, v])
                balance[u] -= value
                balance[v] += value
            with self.subTest(trial=trial):
                self.assertEqual(result["value"], min(cuts))
                self.assertEqual(result["value"], result["cut_capacity"])
                self.assertEqual(balance, [-result["value"]] + [0] * (n - 2) + [result["value"]])
                self.assertIn(0, result["source_side"])
                self.assertNotIn(n - 1, result["source_side"])

    def test_exact_assignment_against_load_state_dp(self):
        rng = random.Random(303)
        for trial in range(60):
            n, m = rng.randint(0, 6), rng.randint(0, 4)
            capacities = [rng.randint(0, 2) for _ in range(m)]
            costs = [[rng.randint(0, 8) if rng.random() < .65 else None for _ in range(m)] for _ in range(n)]
            expected = partition_assignment_reference(costs, capacities)
            result = exact_capacitated_assignment(costs, capacities)
            with self.subTest(trial=trial):
                self.assertEqual(result["status"], "optimal")
                self.assertEqual(result["objective"], {"assigned": expected[0], "cost": expected[1]})
                assigned = result["assignment"]
                self.assertEqual(result["complete"], all(v is not None for v in assigned))
                self.assertTrue(all(v is None or costs[i][v] is not None for i, v in enumerate(assigned)))
                self.assertTrue(all(assigned.count(r) <= capacities[r] for r in range(m)))

    def test_exact_assignment_preserves_priority_and_partial(self):
        result = exact_capacitated_assignment([[0, 100], [1, None]], [1, 1])
        self.assertEqual(result["objective"], {"assigned": 2, "cost": 101})
        self.assertEqual(result["assignment"], [1, 0])
        partial = exact_capacitated_assignment([[1], [2]], [1])
        self.assertFalse(partial["complete"])
        self.assertEqual(partial["assignment"], [0, None])

    def test_exact_assignment_skip_does_not_enumerate(self):
        with patch("examples.methods.allocation.product", side_effect=AssertionError("must not enumerate")):
            result = exact_capacitated_assignment([[1, 2]] * 20, [20, 20], max_states=100)
            self.assertEqual(result["status"], "skipped")
            self.assertIsNone(result["assignment"])
            self.assertIsNone(result["objective"])
            self.assertEqual(exact_capacitated_assignment([[]] * 201, [])["reason"], "item_limit")

    def test_allocation_input_validation(self):
        invalid = [lambda: bipartite_matching([[0]], 0), lambda: bipartite_matching([[True]], 2),
                   lambda: maximum_flow(2, [(0, 1, -1)], 0, 1), lambda: maximum_flow(2, [], 0, 0),
                   lambda: exact_capacitated_assignment([[1]], []),
                   lambda: exact_capacitated_assignment([[True]], [1]),
                   lambda: exact_capacitated_assignment([[-1]], [1]),
                   lambda: exact_capacitated_assignment([[1]], [False]),
                   lambda: exact_capacitated_assignment([], [], max_states=1_000_001)]
        for operation in invalid:
            with self.assertRaises(ValueError):
                operation()


class LocalSearchExamplesTests(unittest.TestCase):
    @staticmethod
    def cost(matrix, tour):
        return 0 if len(tour) < 2 else sum(matrix[a][b] for a, b in zip(tour, tour[1:] + tour[:1]))

    def test_directed_tours_preserve_members_and_never_worsen(self):
        rng = random.Random(401)
        for trial in range(40):
            n = rng.randint(0, 7)
            matrix = [[0 if a == b else rng.randint(0, 20) for b in range(n)] for a in range(n)]
            initial = list(range(n))
            before = deepcopy((matrix, initial))
            result = improve_tour(matrix, initial, max_evaluations=5000)
            with self.subTest(trial=trial):
                self.assertEqual((matrix, initial), before)
                self.assertEqual(sorted(result["tour"]), initial)
                if n:
                    self.assertEqual(result["tour"][0], initial[0])
                self.assertEqual(result["cost"], self.cost(matrix, result["tour"]))
                self.assertLessEqual(result["cost"], self.cost(matrix, initial))
                self.assertFalse(result["global_optimality_proven"])
                if result["stop_reason"] == "local_optimum":
                    final = result["tour"]
                    for a in range(1, n - 1):
                        for b in range(a + 1, n):
                            candidate = final[:a] + list(reversed(final[a:b + 1])) + final[b + 1:]
                            self.assertGreaterEqual(self.cost(matrix, candidate), result["cost"])

    def test_directed_cost_requires_full_recomputation(self):
        matrix = [[0, 2, 1, 8], [8, 0, 1, 1], [8, 50, 0, 2], [2, 8, 8, 0]]
        # Reversing [1,2] appears favorable using only boundary edges but costs 54.
        self.assertEqual(self.cost(matrix, [0, 1, 2, 3]), 7)
        self.assertEqual(self.cost(matrix, [0, 2, 1, 3]), 54)
        result = improve_tour(matrix, [0, 1, 2, 3])
        self.assertLessEqual(result["cost"], 7)

    def test_budget_and_invalid_inputs(self):
        matrix = [[0 if a == b else 1 for b in range(4)] for a in range(4)]
        result = improve_tour(matrix, [0, 1, 2, 3], max_evaluations=1)
        self.assertEqual(result["stop_reason"], "evaluation_limit")
        self.assertEqual(result["evaluations"], 1)
        invalid = [lambda: improve_tour([[0, 1]], [0]), lambda: improve_tour([[0, 1], [1, 0]], [0, 0]),
                   lambda: improve_tour([[0, 1], [1, 0]], [False, 1]),
                   lambda: improve_tour([[0, -1], [1, 0]], [0, 1]),
                   lambda: improve_tour([], [], max_evaluations=0)]
        for operation in invalid:
            with self.assertRaises(ValueError):
                operation()


class ExecutableExamplesTests(unittest.TestCase):
    def test_read_only_demo_runs_as_a_module(self):
        root = Path(__file__).resolve().parents[1]
        run = subprocess.run([sys.executable, "-m", "examples.methods.demo"], cwd=root,
                             capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual(report["bipartite_matching"]["matched"], 2)
        self.assertEqual(report["exact_capacitated_assignment"]["objective"], {"assigned": 2, "cost": 3})
        self.assertEqual(report["maximum_flow"]["value"], 3)
        self.assertFalse(report["directed_tour_improvement"]["global_optimality_proven"])


if __name__ == "__main__":
    unittest.main()
