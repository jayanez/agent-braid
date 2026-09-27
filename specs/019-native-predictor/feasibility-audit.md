# SPEC-019 feasibility audit before training

**Status:** candidate for human review; no model training or evaluation has run.
**Input:** the fixed-ID/attribute anchor-topology corpus of SPEC-018 at
`46d78a3f6c0b95a5a18458eedb7f90dcefddc777`.

The SPEC-018 producer and verifier were run on every two- and three-operation
anchor assignment in the declared base-size 0–3 domain. The observed counts
were:

| Operations | Rule proposal | Verifier status | Cases |
| --- | --- | --- | ---: |
| 2 | `propose-swap` | `verified-bounded` | 10 |
| 2 | `keep-order` | `verified-bounded` | 20 |
| 3 | `review` | `verified-bounded` | 100 |

Reproduction command from the repository root:

```sh
python3 - <<'PY'
from collections import Counter
from itertools import product
from agent_braid.structured_exchange import ROOT, VERSION, produce, verify

counts = Counter()
for n in range(4):
    base = [{'id': f'b{i}', 'value': f'B{i}'} for i in range(n)]
    anchors = [ROOT] + [item['id'] for item in base]
    for count in (2, 3):
        for assignment in product(anchors, repeat=count):
            operations = [
                {'id': f'o{i}', 'kind': 'insert', 'anchorId': anchor,
                 'newId': f'n{i}', 'value': f'N{i}'}
                for i, anchor in enumerate(assignment)
            ]
            evidence = produce({'model': VERSION, 'base': base,
                                'operations': operations})
            counts[(count, evidence['proposal'], verify(evidence)['status'])] += 1
print(dict(sorted(counts.items())))
PY
```

This is a feasibility observation, not independent verification: both passes
use the same replay implementation. The validity label has no negative class
inside the supported corpus. The rule proposal label has variation, but is an
exact function of operation count and anchor equality. Training a classifier
to reproduce either label would not test an improvement over that rule.
Unsupported operations provide `inconclusive` negative controls for the
verifier, but a model that merely learns their syntax cannot establish
semantic exchange utility and cannot replace deterministic validation.

## Target decision and remaining prerequisites

The founder chose direction 1 on 2026-09-27. The detailed
[workload protocol](workload-protocol.md), source data, privacy review and
family-separated holdout still need review before training. The two directions
and their differing evidence needs are retained here for provenance:

1. **Workload prioritization:** collect privacy-reviewed, prospective candidate
   exchanges and an independently defined usefulness/cost label. Preregister
   the population, annotation procedure, family partition, utility metric,
   abstention policy and a fixed rule baseline before inspecting holdout labels.
   Verifier status remains a separate mandatory gate for any proposed exchange.
2. **Broader exchange semantics:** first define and review a new deterministic
   domain with both supported positive and divergent cases, including its
   observation and verifier contract. Only then preregister a model comparison.
   This would be new semantic work, not an interpretation of the current
   anchored-insert evidence.

The bounded M3 verifier now has founder approval as an experiment. Until the
chosen path has a reviewed dataset protocol and actual data, SPEC-019 T001–T005
remain pending. A null result is
acceptable after a valid protocol; it is not a substitute for an identifiable
target here.
