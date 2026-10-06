# SPEC-033: Implementation plan

## Technical context and scope

Operational engineering for opt-in shadow decisions, per-capability promotion, drift monitoring, rollback and bounded closure. No automatic online learning, external telemetry export, paid model calls or milestone closure. Python 3.12+; core standard library, optional ML package isolated.
Dependencies: SPEC-029 registered evaluation and SPEC-031 consumers; advanced SPEC-032 features promote independently and may stay deferred. No implementation executes in this planning task.

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

Use immutable registry manifests binding model/tokenizer/head/calibration/policy/capability and observation contract. Shadow mode cannot affect planning or execution. Compare complete decision chains against no-advisor baseline. Promotion uses separately recorded founder/operator scope and empirical budgets. Drift, out-of-domain input or integrity failures trigger deterministic fallback and reversible rollback; retraining is a separate reviewed offline candidate.
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
