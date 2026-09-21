# Counterexamples

Counterexamples are first-class project artifacts. Each entry should contain the smallest reproducible initial state, operations, schedules, observation boundary, divergence, and environment metadata.

Never include secrets, proprietary repositories, or personal data.

## Current controls

Run `python3 -m research.lab.controls` from the repository root.

| ID | State and operations | Observation and divergence |
|---|---|---|
| CE1 | Three zero integers; set x, set y, assign z=x*y | All initial pairs agree, but ABC yields z=1 and ACB yields z=0 |
| CE2 | Zero counter; two split read/write increments | Interleaved result 1 versus serial result 2 |
| CE3 | Visible=0, hidden=0; set hidden to 1 or 2 | Visible projection agrees until a continuation copies hidden |
| CE4 | Zero counter; two identified fetch-and-increments | Equal final counter, different values returned to each instance |
| CE5 | x=y=0; isolated guarded reservations | Each branch satisfies x+y≤1; combined disjoint writes violate it |

Definitions, assertions and operation orders are in [controls.py](../lab/controls.py).
CE1 also has an [interpreter fixture](../../examples/lab/context-dependent.json).
These dependency-free finite examples contain no external resources. Minimality
is not claimed globally. Environment: Python 3.11+; exact integer arithmetic in
controls, bounded integers in the interpreter. See [the lab](../lab/README.md).
