# SPEC-021: Complete bounded M4 alpha runtime

## Purpose and scope

Complete the six candidate M4 deliverables with a model-agnostic, local fixed-patch runtime. This is an engineering track independent of M3/M3.5 datasets, hypotheses and predictor scores. SPEC-020 remains accepted within its original serial contract; this proposal neither rewrites that acceptance nor declares M4 closed.

The proposed alpha accepts 2–4 immutable ordinary-text A/M operations on one immutable Git base, at most 16 changed paths and 256 KiB patch bytes. Source files, index and refs remain read-only; only a newly allocated private result may be written. Bound workers to at most four, with exclusive private indexes and writable object stores. Publish only through one coordinator. Declare and enforce timeout, output and storage budgets before dispatch. Exact defaults and refusal boundaries must be frozen in the versioned contract before execution, not chosen after measurements.

Exclude arbitrary commands, repository code, tests/hooks/filters, arbitrary autonomous-agent effects, source promotion, deployments, HTTP/network services, remote write targets, hostile same-UID actors and power-loss guarantees. No mathematical or scientific validation is claimed. Windows and untested host/platform combinations are outside alpha coverage.

## Authorities

Constitution Articles 0, 2–7, 9, 12–16, 19–25; GOVERNANCE.md; ADRs 0008, 0013, 0014 and 0019; existing operational semantics and versioned contracts. The [ADR 0020 proposal](adr-0020-proposal.md) is feature-local and non-authoritative until separately adopted into the canonical ADR inventory. Adding that authority later requires visible drift reporting and fresh review of affected current assurance records.

## Requirements and acceptance scenarios

- **REQ-001: Unified policy pipeline.**
  - **SC-001:** Given a fixed-patch request and independently verified analysis, when a candidate is planned, then the runtime preserves the existing portable semantics, contracts and uncertainty and keeps analysis authorization false.
  - **SC-002:** Forged certificates, missing coverage and changed inputs are rejected before run allocation.
- **REQ-002: Separate operator authority.**
  - **SC-003:** Given a prepared immutable plan, when the model invokes execution without a separately recorded operator grant, then no durable run is allocated.
  - **SC-004:** Missing, expired, consumed, wrong-destination and changed-plan grants are refused; a tool annotation or returned digest cannot grant authority.
- **REQ-003: Bounded scheduling and isolation.**
  - **SC-005:** Given 2–4 fixed operations with complete dependencies and adapter-verified footprints, when a ready wave is admitted, then isolated workers may prepare concurrently and one coordinator alone publishes checkpoints.
  - **SC-006:** Overlap, unknown reads, shared resources, stale bases, altered dependencies and incomplete traces cause serialization under a separately acknowledged plan or rejection, never implicit parallel admission.
- **REQ-004: Observed effects and consumer verification.**
  - **SC-007:** Given admitted workers, when actual path/mode/blob effects or result trees differ from the manifest, then publication stops and a read-only consumer rejects completion.
  - **SC-008:** Forged terminal reports and altered private objects/state are refused; declared metadata never substitutes for observed adapter evidence.
- **REQ-005: Recovery and transport interruption.**
  - **SC-009:** Given process death, cancellation or host disconnect, when the run is inspected or explicitly resumed, then an independently verified prefix is retained and completed logical operations are not duplicated.
  - **SC-010:** Repeated delivery, worker failure, interrupted publication and abort are tested; unknown outcome remains unknown until verified.
- **REQ-006: Versioned MCP transport.**
  - **SC-011:** Given a pinned supported protocol revision and deterministic peer, when discovery/initialization and tool calls occur, then bounded stdio messages preserve operation identity, evidence and precise refusals.
  - **SC-012:** Unsupported versions, malformed/oversized messages, unknown tools, invalid arguments and cancellation fail according to the pinned revision without starting unauthorized work.
- **REQ-007: Real host compatibility.**
  - **SC-013:** Given installed Codex and Claude Code versions and approved disposable fixtures, when each actual host invokes the adapter, then prepare, authorized execution, refusal and recovery produce independently verifiable records.
  - **SC-014:** A simulated peer or Spec Kit test is not a real host observation. Record host version, negotiated protocol, candidate, platform, transcript redactions and verifier result.
- **REQ-008: Reproducible bounded M4 closure.**
  - **SC-015:** Given all six roadmap deliverables and a frozen candidate, when closure is reviewed, then every exit row has obtained evidence, independent review and a separate founder decision.
  - **SC-016:** Unexecuted or externally blocked checks keep the affected exit row open. Report serial/parallel agreement, unsafe admissions, actual worker overlap, diagnostic quality and all measured cost components.

Each scenario maps to a named prospective procedure in [validation-plan.md](validation-plan.md); assurance obtained evidence is empty. Planning procedures are not executable tests. Implementation must replace their references with actual tests and captured evidence before validation or closure.

## Scientific boundaries and compatibility

Observation remains private tracked Git trees, checkpoint order, declared and observed adapter footprints, runtime metadata and transport outcomes. Concurrency claims concern isolated fixed-patch preparation with serialized publication, not arbitrary concurrent interleaving. A host may propose patches; it cannot expand the admitted operation language. Reads must be derived from exact patch/base preconditions and observed adapter accesses; unknown reads remain unknown and cannot qualify for parallel admission.

The core retains zero runtime dependencies. Any MCP dependency is optional, isolated and pinned after a justified SDK/license decision. Analysis, execution and transport have separately versioned contracts. Preserve existing command behavior and `executionAuthorization: false` in legacy analysis/replay reports. Operator authority is an explicit acknowledgement within a trusted local ownership boundary, not authentication against a hostile process sharing the same UID.

Hypothesis H1: bounded concurrent preparation can recover useful parallelism with acceptable measured overhead. Zero unsafe admissions and equivalent verified serial results are requirements; a speedup is a hypothesis, not a demanded positive finding. A negative or inconclusive performance result requires a founder go/no-go decision on usefulness before whole-M4 closure.

## Evidence and unresolved questions

Planned: deterministic protocol peers, negative controls, serial-reference comparisons, fresh Darwin/Linux reproductions, actual Codex/Claude Code transcripts, independent Luna review and exact-candidate founder acceptance. Obtained for this expansion: none. SPEC-020 evidence supports only the accepted serial increment.

G0 is the decision on scope, closure criteria and ADR 0020. G1 freezes a protocol revision supported by both actual hosts, exact host versions, optional SDK choice and numerical resource budgets. No compatibility is inferred from the latest published protocol. Real host exercises require access, explicit fixture approval and a recorded model/token or subscription cost boundary; they are not run through CI credentials implicitly. See [decision-packet.md](decision-packet.md).
