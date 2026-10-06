# SPEC-027: Runtime execution refinement contracts

## Purpose and scope

Close the documented next-step gap between private fixed-patch results and source promotion, code-check execution and external adapters. Deliver contract proposals, dry-run controls and capability-specific feasibility decisions. This feature does not implement or authorize any of those expanded runtime capabilities. It preserves SPEC-020 acceptance, SPEC-021 NO-GO and current grant scopes.

## Authorities

Clause zero; Articles 1–7, 9, 12–16, 19–25; Governance; ADRs 0013/0014/0019/0020; portable semantics and current runtime contracts. Any expanded execution decision requires an ADR and founder adoption before its separate implementation feature proceeds.

## Requirements and acceptance scenarios

### REQ-001 — Define the refinement gap and separate authority for each expanded capability.

**SC-001:** Given the accepted private Git result and a proposed broader operation, when a capability contract is checked, then each abstract operation, observation, isolation premise and grant is explicit; current grants cannot authorize expansion.

### REQ-002 — Specify guarded source-ref promotion with a recoverable exclusive boundary.

**SC-002:** Given a verified result and unchanged declared target base, when a disposable promotion dry-run is compared with stale/ref/worktree/crash controls, then only the reviewed exact target and tree can be proposed; any dirty/attached/stale/unknown target is refused without changing it.

### REQ-003 — Require enforceable isolation before any project-code check execution.

**SC-003:** Given a declared command/resource budget and a candidate isolation boundary, when escape, write, network and exhaustion probes are reviewed, then unsupported controls produce NO-GO and no project code is admitted; test success is not semantic commutation.

### REQ-004 — Specify external effects and partial failure without treating compensation as inverse.

**SC-004:** Given an abstract external request with idempotency/response/failure contract, when a simulated retry or failure-after-effect occurs, then attempt identity and visible effects persist; ambiguous success remains unresolved and no automatic resend or rollback claim follows.

### REQ-005 — Turn each refinement assessment into an explicit next implementation or rejection decision.

**SC-005:** Given the dry-run evidence and proposed ADR text, when the decision packet is reviewed, then GO requires a separately adopted ADR, versioned contracts and authorization; NO-GO/watch/rejected is an actionable final assessment and cannot close M4.

## Scientific boundaries and compatibility

Dry-runs use owned disposable repositories and abstract simulators only. Source-ref changes, arbitrary repository code and live external writes stay excluded. A Git tree or passing tests cannot supply semantic equivalence, complete effect coverage or production assurance. Hashes identify bytes and are not signatures or permissions. Legacy contracts remain unchanged; proposed new contract versions live under this spec until adopted.

## Evidence and unresolved questions

Planned outputs are a refinement matrix, proposed ADR, exact negative-control manifests and per-capability decisions. Obtained evidence is empty and human review pending. If no compatible isolation backend is installed, report it as a feasibility limitation, without installing or weakening isolation. Concrete external providers and payload rights must be selected and reviewed in later adapter-specific contracts.
