# Prospective validation

No acceptance check has run, no host behavior has been observed, no probe has been run and nothing in the ledger exists. This sketch has only planning contracts; every implementation procedure is blocked by gate G2 (see [spec](spec.md), [tasks](tasks.md), [contracts](contracts/README.md)). Procedure ids match `assurance.json` (`procedure_req_001` to `procedure_req_005`) and the requirement and scenario ids of `spec.md`.

## Gate map

| Procedure | Status | Executed checks | Pending checks |
|---|---|---|---|
| 001 | Documents and decisions, actionable now | Structural validators only | Founder decision, independent review, G2 disposition |
| 002 | Actionable now (offline, schema and fixtures only) | Planning check with the pinned `jsonschema` package | Repeat in a reviewed test if G2 opens |
| 003 | Decisions actionable now; probes and recorder blocked by G2 | None | Probe receipts HV-L1 to HV-L8, G1 late-notice-harm record, post-HV-L7 decision |
| 004 | Documentation review, actionable now | None | Review |
| 005 | Actionable now | Structural validators only | Gate results GA and GN, review, founder closure |

Common controls: a positive case, adversarial input, drift of the host shape and unavailable observation. Failures, missingness and costs are retained; negative and inconclusive results are recorded as such. Executed checks are kept apart from pending human and externally blocked checks. Planned tests use `unittest` and synthetic fixtures; no real transcript, session record or repository text is read.

## procedure_req_001

Trace: REQ-001 / SC-001. Tasks: T001, T002.

Given the specs/039 coordination route, review `contracts/coordination-contract.md` and `tasks.md`.

- Check that each of the four parts has rules, failure cases and a conformance statement; that the contract says it adopts nothing, that G2 is decided after G1 and opens only after GN passes, and that the retention and deletion rule is stated as a precondition.
- Check that no task creates source, test, script or companion-package files.
- Run `.venv-speckit/bin/python -m scripts.validate_spec_kit` (structure only; a text check cannot verify a decision).

Expected observation: contract complete and unadopted; nothing implemented. Failure handling: a missing part, an implementing task, a claim of adoption or a working contract fails the requirement.

## procedure_req_002

Trace: REQ-002 / SC-002. Task: T003.

Given `contracts/push-settings.schema.json` and the SPEC-057 `orchestration-settings` schema, run offline with the pinned `jsonschema` package:

- Both schemas pass `check_schema`; `push-settings.example.json` validates against the SPEC-057 schema; `push-settings-extension.example.json` validates against the extension schema.
- `push-resolution.example.json` validates against `#/$defs/resolvedDelivery`; `push-resolution-active-while-pull.invalid.json` is rejected.
- A coherent active resolution (push, megaphone, a transport and a receipt) validates; a receipt `hostVersion` or `sha256` with a trailing line feed, and a receipt path with a bidirectional, zero-width, space or newline character, are rejected.
- Check that the transport matrix marks no transport as selected (other than `pull`) or host-observed, and lists the sender-side cross-session post as rejected.

Expected observation: all valid fixtures validate and every negative fixture is rejected. Failure handling: push reported active while the effective mode is pull, an accepted control or bidirectional character, or a schema that cannot be validated (an unavailable observation, not a pass).

## procedure_req_003

Trace: REQ-003 / SC-003. Tasks: T004, T005.

Given the gates, review the G1 record and the probe receipts when they exist.

- Confirm the G1 protocol defines the late-notice-harm measure before its freeze; without it, and without a citing record, the Megaphone and the Doorbell stay disabled.
- Probes HV-L1 to HV-L8 are launched by the orchestrating session through workflows or derived sessions on a scratch repository, each only after the founder's individual authorization, with log-only scripts prepared by an agent; receipts hold counts and booleans with the host version and are pinned under `specs/059-claude-orchestration-ledger/evidence/` (not created here).
- Confirm a recorded post-HV-L7 decision before any recorder exists; if the hook payload cannot carry an agent identifier the recorder is not built.

Expected observation: no strategy enabled and no recorder built without its record. Failure handling: an enabled strategy without a record, a recorder before the decision, a complete-coverage claim, or an attributed orchestrator or human edit fails the requirement.

## procedure_req_004

Trace: REQ-004 / SC-004. Task: T006.

Review `contracts/interop-adapters.md` and the specification: documentation only, every format unconfirmed, no adapter, no write into another tool, and the exclusions of the specification present.

Expected observation: no adapter, lease, main-plugin hook or telemetry field. Failure handling: any of those, or a claim that the ledger replaces another tool, fails the requirement.

## procedure_req_005

Trace: REQ-005 / SC-005. Tasks: T007, T008.

Review the specification, contract and tracking drafts for claim discipline: hypotheses separate from requirements; GA not `fail` and GN `pass` as preconditions to plan G2; no prevention, speed, novelty, read-notice or host-behavior claim without a receipt; obtained evidence empty; human review pending; nothing frozen or approved; "never implemented" recorded as valid. Run `scripts/sync_github_tracking.py source` and check that `tracking-drafts.json` has milestone `null` and publication forbidden.

Expected observation: no unsupported claim. Failure handling: a speed, prevention or novelty claim, an inconclusive gate treated as passed, or inferred approval fails the requirement.
