# SPEC-030: Own non-generative neural decision experiment

## Purpose and scope

Implement and compare native decoder/pointer and encoder/option-scoring prototypes using approved base models. No Laya or Strands package, checkpoint, adapter, runtime service or copied corpus is a product dependency.

Status: draft planning, human review pending. Dependencies: SPEC-028 core and SPEC-029/T008 pre-fit review; SPEC-019 remains an independent linear baseline, not silently expanded.
Milestone: S1.2 — Native decision model. See the [program](../028-system-one-core/program.md)
and [source-backed analysis](../028-system-one-core/reference-analysis.md).

User scenarios: an analyzer operator requests bounded advice and inspectable reasons;
a host gets a precise abstention/fallback when input is unsupported; a maintainer
compares decision quality and complete cost without weakening semantic verification.

## Authorities

Constitution clause zero and Articles 2–7, 9, 12–16, 19–25; GOVERNANCE.md;
ADRs 0017, 0019, 0020; operational semantics; claim discipline; existing versioned
contracts. Proposed architecture choices stay feature-local until separately adopted.
No constitutional amendment, runtime authorization or scientific claim is implied.

## Requirements and acceptance scenarios

- **REQ-001 — Native artifacts and license provenance.** Use independently implemented heads and approved pinned base-model revisions; manifest tokenizer, head, adapter, data and licenses.
  - **SC-001:** Given a model or corpus without approved provenance, when loading or training begins, then it is refused without downloading or evaluating; neither reference project is imported.
- **REQ-002 — Dynamic option scoring.** Return one finite logit per requested option with explicit masking and no autoregressive decoding.
  - **SC-002:** Given unseen option IDs, variable cardinality and a tiny local backbone, when each native prototype runs, then option identities and masked probabilities are preserved and no generation method is called.
- **REQ-003 — Bounded reuse correctness.** Shared-prefix reuse must fork attention and recurrent state correctly and preserve uncached results.
  - **SC-003:** Given different questions sharing a state and an unsupported cache layout, when cached and uncached paths are compared, then probabilities match declared numeric tolerance; unsupported cache falls back visibly without state sharing.
- **REQ-004 — Reproducible offline training.** Freeze data, objective, architecture, splits and seeds before training; calibration stays disjoint.
  - **SC-004:** Given an approved pre-fit manifest and finite budget, when training and calibration execute, then own artifacts bind all inputs and failed/aborted seeds are retained; no test data affects fitting.
- **REQ-005 — Backend parity and numerical failure.** Check CPU reference plus available accelerator/precision variants at identical checkpoints and prompts.
  - **SC-005:** Given quantization, OOM, NaN or backend option reorder, when parity and robustness controls run, then decision changes and tolerances are reported; unsupported hardware has no claimed support.
- **REQ-006 — Evidence-based selection.** Select architecture and deployment size by preregistered quality, risk, total cost and memory constraints.
  - **SC-006:** Given a slower pointer head or weaker encoder and complete paired results, when selection is reviewed, then rules/linear/encoder/decoder/no-model outcomes remain possible; no model is promoted on public README numbers.

## Scientific boundaries and compatibility

Hypothesis H1: A non-generative decision head may improve transferable typed decisions over a linear advisor; the cheaper encoder or rules may win.
Heuristic confidence is not a proof of effects, commutation, confluence, braid laws
or execution safety. Preserve SPEC-019 eligibility/label construct and SPEC-021 G4
NO-GO; this track cannot close M3.5 or M4. Legacy versions and default behavior remain
unchanged; planned APIs/extras are additive and need their own contract review.

## Clarifications and unresolved decisions

The user requests own analogous capabilities, no upstream package/model integration,
an unbiased comparison and complete Spec Kit implementation planning. Public repository
documents remain English; the user-facing explanation is Spanish. Starting with typed
Strands-like contracts does not preselect a decoder model. Unknowns that do not block
planning are explicit implementation gates: consented source/yield, available deployment
hardware, paid/training budgets, final base-model rights and per-capability promotion.
No dataset, hardware support or approval has been invented. Remote delivery authorization
is tracked separately from feature acceptance.

## Evidence and unresolved questions

Source inspection is in the analysis manifest; planned validation is in
[validation-plan.md](validation-plan.md). Feature/model/workload acceptance evidence:
none. All obtained_evidence arrays are empty and human_review is pending. Passing
planning validators establishes artifact structure, not implementation or utility.
