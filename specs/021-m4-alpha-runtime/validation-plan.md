# Prospective validation procedures

Status: planning only. These procedures exist as traceability targets for draft
assurance; none is executable evidence. Each implementation task must create actual
tests, replace these references, and record results before stage validated.

## SC-001 — Unified policy pipeline

Given a fixed-patch request and independently verified analysis, when a candidate is planned, then the runtime preserves the existing portable semantics, contracts and uncertainty and keeps analysis authorization false.

Planned automated target: `tests/test_m4_alpha_pipeline.py`; stable procedure `SC-001`.
Retain exact candidate/input hashes, observed output, verifier status and refusal
or prefix details. Obtained evidence: none.

## SC-002 — Unified policy pipeline

Forged certificates, missing coverage and changed inputs are rejected before run allocation.

Planned automated target: `tests/test_m4_alpha_pipeline.py`; stable procedure `SC-002`.
Retain exact candidate/input hashes, observed output, verifier status and refusal
or prefix details. Obtained evidence: none.

## SC-003 — Separate operator authority

Given a prepared immutable plan, when the model invokes execution without a separately recorded operator grant, then no durable run is allocated.

Planned automated target: `tests/test_m4_alpha_authorization.py`; stable procedure `SC-003`.
Retain exact candidate/input hashes, observed output, verifier status and refusal
or prefix details. Obtained evidence: none.

## SC-004 — Separate operator authority

Missing, expired, consumed, wrong-destination and changed-plan grants are refused; a tool annotation or returned digest cannot grant authority.

Planned automated target: `tests/test_m4_alpha_authorization.py`; stable procedure `SC-004`.
Retain exact candidate/input hashes, observed output, verifier status and refusal
or prefix details. Obtained evidence: none.

## SC-005 — Bounded scheduling and isolation

Given 2–4 fixed operations with complete dependencies and adapter-verified footprints, when a ready wave is admitted, then isolated workers may prepare concurrently and one coordinator alone publishes checkpoints.

Planned automated target: `tests/test_m4_alpha_scheduler.py`; stable procedure `SC-005`.
Retain exact candidate/input hashes, observed output, verifier status and refusal
or prefix details. Obtained evidence: none.

## SC-006 — Bounded scheduling and isolation

Overlap, unknown reads, shared resources, stale bases, altered dependencies and incomplete traces cause serialization under a separately acknowledged plan or rejection, never implicit parallel admission.

Planned automated target: `tests/test_m4_alpha_scheduler.py`; stable procedure `SC-006`.
Retain exact candidate/input hashes, observed output, verifier status and refusal
or prefix details. Obtained evidence: none.

## SC-007 — Observed effects and consumer verification

Given admitted workers, when actual path/mode/blob effects or result trees differ from the manifest, then publication stops and a read-only consumer rejects completion.

Planned automated target: `tests/test_m4_alpha_effects.py`; stable procedure `SC-007`.
Retain exact candidate/input hashes, observed output, verifier status and refusal
or prefix details. Obtained evidence: none.

## SC-008 — Observed effects and consumer verification

Forged terminal reports and altered private objects/state are refused; declared metadata never substitutes for observed adapter evidence.

Planned automated target: `tests/test_m4_alpha_effects.py`; stable procedure `SC-008`.
Retain exact candidate/input hashes, observed output, verifier status and refusal
or prefix details. Obtained evidence: none.

## SC-009 — Recovery and transport interruption

Given process death, cancellation or host disconnect, when the run is inspected or explicitly resumed, then an independently verified prefix is retained and completed logical operations are not duplicated.

Planned automated target: `tests/test_m4_alpha_recovery.py`; stable procedure `SC-009`.
Retain exact candidate/input hashes, observed output, verifier status and refusal
or prefix details. Obtained evidence: none.

## SC-010 — Recovery and transport interruption

Repeated delivery, worker failure, interrupted publication and abort are tested; unknown outcome remains unknown until verified.

Planned automated target: `tests/test_m4_alpha_recovery.py`; stable procedure `SC-010`.
Retain exact candidate/input hashes, observed output, verifier status and refusal
or prefix details. Obtained evidence: none.

## SC-011 — Versioned MCP transport

Given a pinned supported protocol revision and deterministic peer, when discovery/initialization and tool calls occur, then bounded stdio messages preserve operation identity, evidence and precise refusals.

Planned automated target: `tests/test_m4_alpha_mcp.py`; stable procedure `SC-011`.
Retain exact candidate/input hashes, observed output, verifier status and refusal
or prefix details. Obtained evidence: none.

## SC-012 — Versioned MCP transport

Unsupported versions, malformed/oversized messages, unknown tools, invalid arguments and cancellation fail according to the pinned revision without starting unauthorized work.

Planned automated target: `tests/test_m4_alpha_mcp.py`; stable procedure `SC-012`.
Retain exact candidate/input hashes, observed output, verifier status and refusal
or prefix details. Obtained evidence: none.

## SC-013 — Real host compatibility

Given installed Codex and Claude Code versions and approved disposable fixtures, when each actual host invokes the adapter, then prepare, authorized execution, refusal and recovery produce independently verifiable records.

Planned automated target: `tests/test_m4_alpha_hosts.py`; stable procedure `SC-013`.
Retain exact candidate/input hashes, observed output, verifier status and refusal
or prefix details. Obtained evidence: none.

## SC-014 — Real host compatibility

A simulated peer or Spec Kit test is not a real host observation. Record host version, negotiated protocol, candidate, platform, transcript redactions and verifier result.

Planned automated target: `tests/test_m4_alpha_hosts.py`; stable procedure `SC-014`.
Retain exact candidate/input hashes, observed output, verifier status and refusal
or prefix details. Obtained evidence: none.

## SC-015 — Reproducible bounded M4 closure

Given all six roadmap deliverables and a frozen candidate, when closure is reviewed, then every exit row has obtained evidence, independent review and a separate founder decision.

Planned automated target: `tests/test_m4_alpha_closure.py`; stable procedure `SC-015`.
Retain exact candidate/input hashes, observed output, verifier status and refusal
or prefix details. Obtained evidence: none.

## SC-016 — Reproducible bounded M4 closure

Unexecuted or externally blocked checks keep the affected exit row open. Report serial/parallel agreement, unsafe admissions, actual worker overlap, diagnostic quality and all measured cost components.

Planned automated target: `tests/test_m4_alpha_closure.py`; stable procedure `SC-016`.
Retain exact candidate/input hashes, observed output, verifier status and refusal
or prefix details. Obtained evidence: none.

## Measurement protocol

Before runs, freeze owned fixture hashes, platform and version matrix, cold/warm
policy, repetition count and per-run budgets. Include dependency chains, disjoint
ready waves, overlapping edits, stale inputs, undeclared reads/shared resources,
worker failure, budget exhaustion, cancellation, corrupt grants and duplicate calls.
Use serial execution with the same semantics and limits as the correctness reference.
Record actual worker start/end overlap; launching multiple workers alone is insufficient.
Verify all admitted schedules in the supported small domain. Count unsafe admissions
and retain every failed/refused case. Include startup, preparation, coordinator,
verification, wall/CPU/storage cost and real-host cost, with missing metrics explicit.
Two actual host sequences must each cover prepare, authorized execute, refusal,
disconnect/cancel and explicit verified recovery; synthetic peers cover deterministic
transport negatives and cannot replace actual host records.
