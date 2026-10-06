# SPEC-030: Implementation plan

## Technical context and scope

Implement and compare native decoder/pointer and encoder/option-scoring prototypes using approved base models. No Laya or Strands package, checkpoint, adapter, runtime service or copied corpus is a product dependency. Python 3.12+; core standard library, optional ML package isolated.
Dependencies: SPEC-028 core and SPEC-029/T008 pre-fit review; SPEC-019 remains an independent linear baseline, not silently expanded. No implementation executes in this planning task.

## Constitution check before research

Articles 2/4/6/12/13: preserve verification and concurrency/authority boundaries.
Articles 5/7/14/15/16: keep effects, decision stages and provenance inspectable.
Articles 0/9/19/20/23/24/25: preserve falsifiability, actual workloads and separate
analysis/execution/research. No MUST conflict or SHOULD waiver is proposed.

## Research, assumptions and alternatives

See [research.md](research.md), the shared source analysis and the common
[evaluation protocol](../029-system-one-evaluation/evaluation-protocol.md).
Consent, sampling, eligibility, complete blind holdout annotation attempts and
group/class/calibration feasibility precede fitting. Rules, linear, encoder,
decoder and no-model results are all legitimate alternatives.

## Design and compatibility

A causal backbone with its language-model head removed scores dynamically provided option representations against a final decision representation. A bidirectional encoder alternative scores option markers with shared parameters. Train own heads/adapters. Compare frozen encoders, supervised cross-entropy, ordinal soft targets and narrowly approved distillation; add proper-scoring/reward training only through a separately preregistered ablation. Pointer addressing removes slot-specific weights but does not prove order invariance under causal positions.
Follow [data-model.md](data-model.md) and [contracts/interface.md](contracts/interface.md).
The contract is a proposal; no core schema, ADR authority or accepted evidence changes.
Keep backend/request/capability/policy/calibration identities immutable. No copied
reference weights/data, trust_remote_code, automatic network dependency or hidden
effect-authority inference. Artifact/licensing and host/device parity are explicit.

## Validation strategy

Each REQ/SC maps to the assurance record and [validation-plan.md](validation-plan.md).
Tasks give target files, prerequisites, verification and evidence. Retain refusal,
malformed/non-finite input, stale identities, overflow, biased labels, absent calibration,
unknown domains, cancellation and forged-authority controls. Synthetic checks are
structural/software evidence; workload gains require the prospective paired protocol.
Record full cost, sparse groups, proxy labels and null/negative outcomes.

## Constitution check after design

Advice stays heuristic and executionAuthorization false; deterministic verification,
operator grants, normalizer meaning, observation contract and accepted scientific
domains remain unchanged. Feature-local ADR proposal references current authorities.

## Human review and unresolved decisions

Review planned interfaces and evidence gates before implementation. Source-rights/yield,
deployment envelope, paid/model/training budget and promotion are separate decisions.
Planning review does not authorize collection/training, execution or release.

Publication base and reviewed authority drift: [context](../028-system-one-core/delivery/publication-context.md).
