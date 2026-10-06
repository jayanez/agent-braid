# SPEC-029: Implementation plan

## Technical context and scope

Research protocol and tooling for permissioned, representative decision data and paired comparisons. Synthetic conformance cases are never counted as real workload utility. Python 3.12+; core standard library, optional ML package isolated.
Dependencies: SPEC-028 contracts; SPEC-019 source feasibility is reusable only inside its original eligible population. No implementation executes in this planning task.

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

Keep decision families separate: exchange assessed-usefulness proxy, effect-review prioritization, analyzer selection, model/tool recommendation and response adequacy. Build a source register, deduplicated manifests, frozen labels, four disjoint group partitions and a paired evaluation harness. Deterministic tools provide semantic outcomes only within their supported domain, never synthetic human utility.
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
