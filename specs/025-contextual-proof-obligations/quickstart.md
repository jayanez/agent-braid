# SPEC-025 planned validation scenarios

Tests, CLI, scripts and proof artifacts below are **PLANNED** and will be created
by T001–T007. This document is a scenario/test design reference, not obtained
evidence. No formal statement has been accepted by this delivery.

## SC-001 explicit premises and source mapping

Planned review protocol `PremiseInventoryReview`: compare T1/T2 and anchored
candidate statements against named semantics and exact source hashes; enumerate
all carriers, quantifiers, equivalences, unproved gaps and claim statuses.

## SC-002 distinguishing continuation witness

Future `ContextualChecksTests.test_terminal_match_with_distinguishing_suffix` in
`tests/test_contextual_lab.py`: hidden-state, enabledness, returned-value and version
witnesses must retain both full configurations and a minimized explicit suffix.

## SC-003 finite coverage, bounds and tamper rejection

Future `ContextualChecksTests.test_suffix_binding_and_bounds`: empty suffix,
explicit matching suffix set, missing/changed suffixes, >6 ops and each cap;
matching yields only equivalent-for-listed-continuations, never universal.

## SC-004 omitted-premise controls and trace safety

Future `ContextualControlsTests.test_omitted_premises_and_event_order`: hidden
state, returns, initial-context-only pairs, guards/versions, event chronology and
noncommuting controls plus disjoint positives; retain exact trace disagreements.

## SC-005 anchored proof packet and model exclusions

Planned `AnchoredProofReview` plus future
`ContextualProofMappingTests.test_anchored_relations_and_exclusions`: verify carrier,
set-union/flattening, residual mapping, involutivity and far/adjacent conventions.
Delete/nested/nondeterministic input remains excluded; finite cross-check cannot
set the formal acceptance status.

## SC-006 CoAgent comparison readiness

Planned review protocol `CoAgentFeasibilityReview`: verify immutable primary
source/artifact references, available rights, typed assumption mapping and gaps.
Unavailable/noncomparable yields documented abstention. No automatic execution.

## SC-007 proof/tool review and independent evidence status

Planned review protocol `ProofAndToolDecisionReview`: assess a named proof gap,
handwritten/mechanized options, trusted base and costs; record actual reviewer
conclusions without inferring approval or requiring tool adoption.

## Planned implementation commands

```sh
python3 -m unittest discover -s tests -p 'test_contextual_lab.py' -v
python3 -m research.contextual_lab check examples/contextual-lab/manifest.json --output specs/025-contextual-proof-obligations/evidence/continuations.json
python3 -m research.contextual_lab verify specs/025-contextual-proof-obligations/evidence/continuations.json
python3 scripts/crosscheck_contextual_proof_mapping.py --manifest examples/contextual-lab/manifest.json --output specs/025-contextual-proof-obligations/evidence/mapping.json
python3 scripts/validate_change.py --base develop --profile quick
python3 scripts/validate_change.py --base develop --profile pr
```

Capture raw output, source/input/tool hashes, observation/suffix set, counts and
exact commands. Reproduce finite results in an independent clone. Submit a frozen
candidate for specific proof review; a passing profile, finite corpus or LLM review
cannot alone establish universal formal correctness or founder approval.
