"""Graph examples with numbered vertices and explicit directedness."""

from collections import deque
import heapq

from ._validation import edge_list, integer, vertex


def bfs(node_count, edges, source, *, directed=False):
    """Return (distance, parent), using None for unreachable vertices."""
    edges = edge_list(node_count, edges)
    vertex(source, node_count, "source")
    if type(directed) is not bool:
        raise ValueError("directed must be bool")
    adjacency = [[] for _ in range(node_count)]
    for u, v in edges:
        adjacency[u].append(v)
        if not directed:
            adjacency[v].append(u)
    for row in adjacency:
        row.sort()
    distance, parent = [None] * node_count, [None] * node_count
    distance[source] = 0
    queue = deque([source])
    while queue:
        u = queue.popleft()
        for v in adjacency[u]:
            if distance[v] is None:
                distance[v], parent[v] = distance[u] + 1, u
                queue.append(v)
    return distance, parent


def dijkstra(node_count, edges, source, *, directed=True):
    """Nonnegative integer edge costs; parallel edges and zero costs are allowed."""
    edges = edge_list(node_count, edges, weighted=True, nonnegative=True)
    vertex(source, node_count, "source")
    if type(directed) is not bool:
        raise ValueError("directed must be bool")
    adjacency = [[] for _ in range(node_count)]
    for u, v, weight in edges:
        adjacency[u].append((v, weight))
        if not directed:
            adjacency[v].append((u, weight))
    for row in adjacency:
        row.sort()
    distance, parent = [None] * node_count, [None] * node_count
    distance[source] = 0
    heap = [(0, source)]
    while heap:
        current, u = heapq.heappop(heap)
        if current != distance[u]:
            continue
        for v, weight in adjacency[u]:
            proposed = current + weight
            if distance[v] is None or proposed < distance[v]:
                distance[v], parent[v] = proposed, u
                heapq.heappush(heap, (proposed, v))
    return distance, parent


def topological_sort(node_count, edges):
    """Return a lexicographically smallest order; reject any directed cycle."""
    edges = edge_list(node_count, edges)
    adjacency = [[] for _ in range(node_count)]
    degree = [0] * node_count
    for u, v in edges:
        adjacency[u].append(v)
        degree[v] += 1
    ready = [u for u in range(node_count) if degree[u] == 0]
    heapq.heapify(ready)
    result = []
    while ready:
        u = heapq.heappop(ready)
        result.append(u)
        for v in adjacency[u]:
            degree[v] -= 1
            if degree[v] == 0:
                heapq.heappush(ready, v)
    if len(result) != node_count:
        raise ValueError("directed cycle prevents a topological order")
    return result


class DisjointSet:
    """Union by size with path compression; indices are 0..size-1."""

    def __init__(self, size):
        integer(size, "size", 0)
        self.parent = list(range(size))
        self.sizes = [1] * size
        self.components = size

    def find(self, value):
        vertex(value, len(self.parent))
        root = value
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[value] != value:
            following = self.parent[value]
            self.parent[value] = root
            value = following
        return root

    def union(self, left, right):
        a, b = self.find(left), self.find(right)
        if a == b:
            return False
        if self.sizes[a] < self.sizes[b] or (self.sizes[a] == self.sizes[b] and a > b):
            a, b = b, a
        self.parent[b] = a
        self.sizes[a] += self.sizes[b]
        self.components -= 1
        return True


def minimum_spanning_forest(node_count, edges):
    """Kruskal on an undirected graph; a disconnected input returns a forest."""
    edges = edge_list(node_count, edges, weighted=True)
    normalized = sorted((weight, min(u, v), max(u, v)) for u, v, weight in edges)
    sets = DisjointSet(node_count)
    chosen, cost = [], 0
    for weight, u, v in normalized:
        if sets.union(u, v):
            chosen.append((u, v, weight))
            cost += weight
    return {"edges": chosen, "total_cost": cost, "components": sets.components}
