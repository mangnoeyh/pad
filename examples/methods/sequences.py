"""Array, interval and integer dynamic-programming examples."""

from bisect import bisect_right
from collections import deque

from ._validation import integer, sequence


def prefix_sums(values):
    """Return n+1 sums; sum over [left, right) is p[right] - p[left]."""
    sequence(values, "values")
    result = [0]
    for value in values:
        result.append(result[-1] + integer(value, "value"))
    return result


class Fenwick:
    """Mutable integer point-add/range-sum structure, with half-open ranges."""

    def __init__(self, values):
        sequence(values, "values")
        self.size = len(values)
        self.tree = [0] * (self.size + 1)
        for index, value in enumerate(values):
            self.add(index, value)

    def add(self, index, delta):
        integer(index, "index", 0, self.size - 1)
        integer(delta, "delta")
        index += 1
        while index <= self.size:
            self.tree[index] += delta
            index += index & -index

    def prefix(self, end):
        integer(end, "end", 0, self.size)
        total = 0
        while end:
            total += self.tree[end]
            end -= end & -end
        return total

    def range_sum(self, start, end):
        integer(start, "start", 0, self.size)
        integer(end, "end", start, self.size)
        return self.prefix(end) - self.prefix(start)


def sliding_maximum(values, width):
    """Maximum for each full window; width > len(values) gives no windows."""
    sequence(values, "values")
    integer(width, "width", 1)
    for value in values:
        integer(value, "value")
    candidates, result = deque(), []
    for index, value in enumerate(values):
        while candidates and candidates[0] <= index - width:
            candidates.popleft()
        while candidates and values[candidates[-1]] <= value:
            candidates.pop()
        candidates.append(index)
        if index + 1 >= width:
            result.append(values[candidates[0]])
    return result


def _intervals(intervals, weighted=False):
    sequence(intervals, "intervals")
    result = []
    for index, interval in enumerate(intervals):
        sequence(interval, "interval")
        if len(interval) != (3 if weighted else 2):
            raise ValueError("interval has the wrong number of fields")
        start, end = integer(interval[0], "start"), integer(interval[1], "end")
        if end <= start:
            raise ValueError("intervals must have start < end")
        if weighted:
            result.append((start, end, integer(interval[2], "value", 0), index))
        else:
            result.append((start, end))
    return result


def merge_intervals(intervals, *, merge_touching=False):
    """Merge half-open intervals; adjacency is optional, not assumed overlap."""
    intervals = sorted(_intervals(intervals))
    if type(merge_touching) is not bool:
        raise ValueError("merge_touching must be bool")
    result = []
    for start, end in intervals:
        if result and (start < result[-1][1] or (merge_touching and start == result[-1][1])):
            result[-1] = (result[-1][0], max(end, result[-1][1]))
        else:
            result.append((start, end))
    return result


def weighted_interval_schedule(intervals):
    """Maximize additive value on one resource, allowing end == next start."""
    ordered = sorted(_intervals(intervals, weighted=True), key=lambda row: (row[1], row[0], row[3]))
    ends = [row[1] for row in ordered]
    previous, take, best = [], [], [0]
    for index, (start, end, value, original) in enumerate(ordered):
        count = bisect_right(ends, start, 0, index)
        previous.append(count)
        selected = value + best[count]
        take.append(selected > best[-1])
        best.append(max(selected, best[-1]))
    indices, cursor = [], len(ordered)
    while cursor:
        if take[cursor - 1]:
            indices.append(ordered[cursor - 1][3])
            cursor = previous[cursor - 1]
        else:
            cursor -= 1
    indices.reverse()
    return {"value": best[-1], "indices": indices}


def knapsack_01(items, capacity, *, max_cells=1_000_000):
    """Positive integer weights, nonnegative integer values; each item at most once."""
    sequence(items, "items")
    integer(capacity, "capacity", 0)
    integer(max_cells, "max_cells", 1, 10_000_000)
    clean = []
    for item in items:
        sequence(item, "item")
        if len(item) != 2:
            raise ValueError("each item must be (weight, value)")
        clean.append((integer(item[0], "weight", 1), integer(item[1], "value", 0)))
    cells = (len(clean) + 1) * (capacity + 1)
    if cells > max_cells:
        raise ValueError(f"DP cell budget exceeded: {cells} > {max_cells}")
    table = [[0] * (capacity + 1)]
    for weight, value in clean:
        old = table[-1]
        row = old.copy()
        for available in range(weight, capacity + 1):
            row[available] = max(old[available], old[available - weight] + value)
        table.append(row)
    selected, remaining = [], capacity
    for count in range(len(clean), 0, -1):
        if table[count][remaining] > table[count - 1][remaining]:
            selected.append(count - 1)
            remaining -= clean[count - 1][0]
    selected.reverse()
    return {"value": table[-1][capacity], "weight": capacity - remaining, "indices": selected}
