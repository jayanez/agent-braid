# SPDX-License-Identifier: AGPL-3.0-only
"""Finite review checks, not an Agent Braid implementation or general proof.

Run with Python 3. Uses only the standard library and no external effects.
"""

from itertools import combinations, permutations, product


def run(order):
    state = dict(x=0, y=0, z=0)
    for operation in order:
        if operation == "A":
            state["x"] = 1
        elif operation == "B":
            state["y"] = 1
        elif operation == "C":
            state["z"] = state["x"] * state["y"]
        else:
            raise ValueError(operation)
    return state


def check_counterexamples():
    for a, b in combinations("ABC", 2):
        assert run(a + b) == run(b + a)
    outcomes = {"".join(p): run(p) for p in permutations("ABC")}
    assert outcomes["ABC"] != outcomes["ACB"]
    print("CE1: all 3 pairs agree at the initial state; 6 schedules diverge:", outcomes)

    value = 0
    read_a = value
    read_b = value
    value = read_a + 1
    value = read_b + 1
    assert value == 1 and (0 + 1) + 1 == 2
    print("CE2: non-atomic increments lose an update (1 instead of 2).")

    ab, ba = {"visible": 0, "hidden": 2}, {"visible": 0, "hidden": 1}
    observe = lambda s: s["visible"]
    continuation = lambda s: {**s, "visible": s["hidden"]}
    assert observe(ab) == observe(ba)
    assert observe(continuation(ab)) != observe(continuation(ba))
    print("CE3: terminal observation equality is not preserved by continuation.")

    def fetch_add(order):
        value, returned = 0, {}
        for operation in order:
            returned[operation] = value
            value += 1
        return value, returned

    assert fetch_add("AB")[0] == fetch_add("BA")[0]
    assert fetch_add("AB")[1] != fetch_add("BA")[1]
    print("CE4: equal counter states can conceal different per-operation results.")

    # Two isolated guarded transactions: x := 1 if y == 0; y := 1 if x == 0.
    initial = {"x": 0, "y": 0}
    branch_a = {**initial, "x": 1}
    branch_b = {**initial, "y": 1}
    invariant = lambda s: s["x"] + s["y"] <= 1
    merged = {"x": branch_a["x"], "y": branch_b["y"]}
    assert invariant(branch_a) and invariant(branch_b) and not invariant(merged)
    print("CE5: individually valid branches with disjoint writes violate a merged invariant.")


def check_finite_braid():
    group = list(permutations(range(3)))

    def multiply(p, q):
        """p*q means p after q, an algebraic convention, not a task schedule."""
        return tuple(p[q[i]] for i in range(3))

    def inverse(p):
        return tuple(p.index(i) for i in range(3))

    def exchange(a, b):
        return b, multiply(multiply(inverse(b), a), b)

    def adjacent(triple, i):
        result = list(triple)
        result[i:i + 2] = exchange(*result[i:i + 2])
        return tuple(result)

    for a, b in product(group, repeat=2):
        c, d = exchange(a, b)
        assert multiply(a, b) == multiply(c, d)
    for triple in product(group, repeat=3):
        left = adjacent(adjacent(adjacent(triple, 0), 1), 0)
        right = adjacent(adjacent(adjacent(triple, 1), 0), 1)
        assert left == right
    assert len({exchange(a, b) for a, b in product(group, repeat=2)}) == 36
    assert any(exchange(*exchange(a, b)) != (a, b) for a, b in product(group, repeat=2))
    print("S3: 36/36 product checks; 216/216 braid checks; bijective and not involutive.")


if __name__ == "__main__":
    check_counterexamples()
    check_finite_braid()
