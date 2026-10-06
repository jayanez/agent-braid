# Implementation plan

## Technical context and scope

Use current private Git runtime reports/manifests as inputs to a read-only contract-assessment tool, future `scripts/check_runtime_refinement.py`. Store candidate contracts under this spec, not public schemas or adopted ADR directories. Implement only deterministic disposable dry-runs and abstract failure models in this feature; no caller-repository ref writes or project code.

## Constitution check before research

Execution refinement is a premise under Articles 6/12/20, not a consequence of sequential replay or producer certificates. Current grants never carry broader scope. Article 5 requires external results and failures; Article 13 separates properties, methods and verification. MUST conflicts stop the proposed capability.

## Research, assumptions and alternatives

Source promotion is the first assessment because it could make owned results useful without running code. Compare a read-only export/manual integration alternative with a future exclusive CAS promotion boundary. Code checks and live external adapters are independently assessed; neither blocks read-only analysis or private Git use. Do not choose an uninstalled sandbox or buy services to satisfy a proposal.

## Design and compatibility

Promotion candidate: target repository/ref plus expected old object, verified result tree and input/operation identities. A future promotion-specific operator grant must be distinct from existing private execution grants. Acquire an exclusive coordinator boundary, revalidate expected ref and all target worktree/index state, reject dirty or checked-out target refs in the first proposed contract, then compare-and-swap only the exact allowed ref. Preserve recovery intent and before/after object identities. Unknown worktree state, stale base, missing verifier material, unrelated refs, or incompatible ownership is refusal. Dry-run fault injection must classify interruption before/after a proposed CAS; compensation cannot erase an already published effect. Actual implementation requires its separately approved protocol.

Code-check candidate: allowed command argv, immutable checkout, private filesystem writes, explicit environment, no credentials, deny network, wall/output/scratch/process/memory budgets, descendants kill/recovery and observable results. Enumerate controls the installed OS/backend truly enforces. Host CLI commands, Git flags and stdlib wrappers are not a general sandbox. First task is capability discovery/read-only inventory; probes use reviewed harmless synthetic commands only after their boundary is authorized. If writes/network/descendants cannot be enforced, code-check admission is NO-GO. Actual package installs or runner configuration remain outside this feature.

External effects candidate: identify operation/attempt/idempotency key, precondition/version, visible effect/response, ambiguous timeout, duplicate delivery and recovery decision. Exercise the event simulator from SPEC-024 or an independent abstract fixture, never a real service. Define when replay is forbidden, how uncertain success is surfaced and which compensation has its own separate meaning. Select a real adapter only through a later scoped privacy/security/rights review and grant.

## Validation strategy

SC-001..005 map to quickstart scenario contracts. Future `tests/test_runtime_refinement.py` rejects every scope escalation and exercises disposable stale-ref/worktree/crash classification and abstract external failures. Scenario targets are planned, not currently executed tests. Run quick and PR; preserve decision packets whether positive, negative or inconclusive.

## Constitution check after design

No production isolation or real-adapter refinement claim is made by the tool. Proposal acceptance cannot be inferred from dry-run success or this feature's merge.

## Human review and unresolved decisions

Per capability, produce ADR/scope proposal and exact risk/unknown list. Founder adoption, owner rights and operation-specific execution authorization precede separate implementation/use. Rejected refinements end with a supported fallback and reconsideration condition. M4 acceptance remains separate.
