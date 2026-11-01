"""Shared type checks, not business rules or an input-file parser."""


def integer(value, name, minimum=None, maximum=None):
    if type(value) is not int:
        raise ValueError(f"{name} must be an integer (bool is not accepted)")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be at most {maximum}")
    return value


def sequence(value, name):
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{name} must be a list or tuple")
    return value


def vertex(value, n, name="vertex"):
    return integer(value, name, 0, n - 1)


def edge_list(n, edges, weighted=False, nonnegative=False):
    integer(n, "node_count", 0)
    sequence(edges, "edges")
    result = []
    for index, edge in enumerate(edges):
        sequence(edge, f"edges[{index}]")
        if len(edge) != (3 if weighted else 2):
            raise ValueError(f"edges[{index}] has the wrong number of fields")
        u, v = vertex(edge[0], n), vertex(edge[1], n)
        if weighted:
            weight = integer(edge[2], "weight", 0 if nonnegative else None)
            result.append((u, v, weight))
        else:
            result.append((u, v))
    return result
