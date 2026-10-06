# SPEC-032: Implementation plan

## Technical context and scope

Independently implement useful product patterns observed in Laya: CPU optimization, multilingual routing, schema-derived questions, large-catalogue retrieval, batching, lifecycle control and telemetry hooks. Defer browser automation, vision, email parsing, multiple language SDKs and framework-specific adapters until demand and evidence justify separate specs. Python 3.12+; core standard library, optional ML package isolated.
Dependencies: SPEC-028/029 contracts and evaluation; learned extensions require SPEC-030 selection. No advanced feature is an MVP prerequisite. No implementation executes in this planning task.

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

Add optional backend exports with reference parity. Language and task routing use declared support and validated metadata before confidence; unsupported or mixed input defers. Schema compiler supports boolean/enums/ordered rubrics only and rejects arbitrary generation. Shortlisting and tournament plans report all candidates, dropped labels, finalist identity and conditional probabilities. Hook observers cannot mutate sealed inputs or grant authority.
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

## Optional branch ordering and exits

T001 reviews the subset after SPEC-028/T001, without waiting for model selection.
Implement only selected extensions against the accepted core boundary. The schema
compiler and core hooks need no neural model. Export and model lifecycle require
selection of the exact model; learned routing/catalogue use has the same gate.
Routing, exports and catalogue are prerequisites of another extension only when
that extension actually uses them. Wheel validation covers its selected contents.

T008 requires the selected implementation branches and their own evidence, rather
than every advanced feature. A deferred branch records its reason and reconsideration
condition while its task stays pending and its scenarios remain draft with empty
obtained evidence. A schema-only or hooks-only packet can proceed while model research
is blocked; an all-deferred packet is a feasibility result. Packet completion does
not accept the whole spec, waive workload/calibration gates or authorize promotion.

## Constitution check after design

Advice stays heuristic and executionAuthorization false; deterministic verification,
operator grants, normalizer meaning, observation contract and accepted scientific
domains remain unchanged. Feature-local ADR proposal references current authorities.

## Human review and unresolved decisions

Review planned interfaces and evidence gates before implementation. Source-rights/yield,
deployment envelope, paid/model/training budget and promotion are separate decisions.
Planning review does not authorize collection/training, execution or release.

Publication base and reviewed authority drift: [context](../028-system-one-core/delivery/publication-context.md).
