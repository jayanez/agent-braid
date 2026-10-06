# Bounded continuation laboratory

This dependency-free source-checkout package implements SPEC-025's reviewed
experimental [continuation interface](../../specs/025-contextual-proof-obligations/contracts/continuations-v1.md).
It consumes one unchanged integer fixture, two successfully reachable prefixes
with the same consumed original IDs, and an explicit suffix set including empty.
The canonical integer interpreter is unchanged.

```sh
python3 -m research.contextual_lab check examples/contextual-lab/manifest.json --output /absolute/new-report.json
python3 -m research.contextual_lab verify /absolute/new-report.json
python3 -m unittest discover -s tests -p 'test_contextual_lab.py' -v
```

```python
from research.contextual_lab import check, source_bindings, verify

request["sourceBindings"] = source_bindings()  # prospectively pin inspected source
report = check(request)
replay_status = verify(report)
```

Do not refresh bindings to disguise drift or replace evidence from an earlier
source candidate. Verification refuses changed source bytes and stale loaded
interpreter/checker code. The example manifest binds the checked source version;
its expected outcome is independently specified in `examples/contextual-lab/expected.json`.
Any edited source candidate needs a separately generated manifest/evidence capture.

Every fragment maps to a dependency-closed restricted fixture containing original
operation definitions and initial state/versions, then runs a complete schedule
through `research.lab.model.run`. Prefix-plus-suffix replays do not inject arbitrary
configurations or reset version/result history. Reports retain the canonical
fragment outcome separately from the full original pending inventory. That full
inventory is restored **before** the chosen exact/projection observation.

The comparison is the explicitly chosen model observation **plus** enabledness of
remaining original operations. Raw state/results/versions/events/outcomes remain
available even when a projection excludes them. `equivalent-for-listed-continuations`
means this finite product matched for exactly the named suffixes; it never means
all admitted future continuations or universal contextual equivalence. Exact
chronological events can differ even for disjoint writes. No quotient is assumed.

Blocked/error listed paths, error probes or missing/capped work yield inconclusive.
Known dependency/guard/version-disabled probes are recorded as disabled. The minimum
witness is shortest then lexical among **registered** suffixes only. No unsupported
result/event-reading primitive, retry, external action or new operation is admitted.

Logical checks count prefix/suffix configurations, candidate probes and paired
comparisons, including cache hits. Actual interpreter replays, cache hits and
attempted modeled steps have separate counters. Conservative block reservations
for logical checks, steps and report bytes occur before work, so a cap cannot drop
an already executed trace from retained evidence. A reservation can refuse a
block earlier than its eventual actual cost; this yields explicit inconclusive
coverage, not a success. Coverage uses bounded suffix indices in canonical
length/lexical order. There is no wall-clock cutoff.

Requests are bounded to 8,000,000 bytes and reports/verifier recomputation to
16,000,000 bytes. Conservative configuration bounds use actual ASCII-JSON
identifier sizes, maximum result/version integers and complete possible read
maps. Prefix/probe/check blocks reserve full raw outcomes and observation copies
before execution/retention. Capacity exhaustion keeps unvisited suffix indices;
the final exact serialized size is checked. Oversized minimum envelopes reject
before model work. Caller-specified output paths must be fresh, non-symlink and
non-colliding; commands never contact a provider or execute project operations.

The finite controls cover hidden state, guard enabledness, stale versions,
returned values omitted by projection, event chronology, initially matching pairs
that fail after a reachable context, dependencies, partial/error outcomes,
malformed/model-extension refusals, source/report tampering, logical/step/byte
caps, deterministic bytes and exclusive CLI destinations. These are engineering
and bounded semantic observations. Specific proof review, human scientific
acceptance and founder decisions remain pending; all reports state
`proofAccepted: false` and `executionAuthorization: false`.
