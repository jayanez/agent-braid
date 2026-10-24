# Requirements-quality checklist

- [x] Every requirement (REQ-001 to REQ-016) has one scenario, a planned verification procedure and a named test file, receipt location or checker.
- [x] Every task line has the form `- [ ] T001 (REQ-001 SC-001): text`, every requirement is referenced by at least one task, every candidate implementation task begins "Candidate (unreleased, behind the G1 gate):" and every package, release and closure task begins "Blocked by G1 gate GG and ADR adoption:".
- [x] The founder decisions of 2026-10-24 in all three rounds (including the SPEC-059 sketch and the native-controls-only comparison in G1) (split, four surfaces, three lifecycle points, three control outputs with hooks in the main plugin rejected, modes ladder and default, scope precedence with the block floor, guard vocabulary, Mailbox + Whisper, deferred skill and telemetry, market and differentiation wording, staged G1 and EUR 0, the unreleased-candidate rule for arm A3, ADR review now and adoption with the G1 outcome, fail-open recorded, unattributed writers, Article 13 classes, probe launch rule, two separate companions, boundaries) are recorded in the specification's Clarifications; the drafting track's own interpretations are listed separately as proposed and not approved.
- [x] SPEC-057's policy-profile schema, settings schema, ownership module, probes HV-6 to HV-8 and HV-10 and gate G1 are consumed by reference and not edited or duplicated.
- [x] Unconfirmed and inferred host behavior is labelled as such and turned into probes (HV-6 to HV-8, HV-10, GP-1 to GP-5); nothing is asserted as host-observed.
- [x] The guard vocabulary is closed; `allow`, `defer`, input rewriting and grant members are unrepresentable; `executionAuthorization` is false in every schema.
- [x] The coverage boundary (Write and Edit, NotebookEdit only if accepted; Bash only through native settings where recorded; unattributed writers not covered) accompanies every output; the sandbox allowlist semantics are labelled unconfirmed; liveness defaults to advisory; fail-open is recorded, not hidden.
- [x] The critical review's weak claims (hook firing inside workflow agents and teammates, tamper and fail-open, allow semantics, opt-in mechanism, CLI-from-hook bypass of the MCP allowlist, injection, Claim Plane rate, dogfood anecdote) are each addressed in research.md.
- [x] The scope excludes launching, messaging, resuming, authorizing, fan-out, hooks in the main plugin, mods, push, a ledger, speed claims and every host other than Claude Code (listed as not covered).
- [x] HAR.3 (specs/050 T005, T006, T011), SPEC-047 and the SPEC-052 no-go list are cross-referenced; nothing is duplicated and no existing acceptance changes.
- [x] Hypotheses H-OR3, H-GD1 and H-GD2 are separate from requirements, untested, with falsification and inconclusive outcomes valid.
- [x] Obtained evidence is empty, human review is pending, and nothing is frozen, signed, run, installed or approved.
- [x] One surface vocabulary (`workflow-tracks`, `linked-sessions`, `agent-teams`, `batch`) is used in the specification, the contracts, the matrix and the drafts.
- [x] A whole-command refusal is an error with a code from SPEC-057's `command-error.schema.json` and no result; a per-unit `not-observed`, a partial envelope and a recorded truncation are results; the mapping is in `contracts/README.md`.
- [x] The escaping definition is SPEC-057's, reused byte for byte; the residual semantic prompt-injection risk (the cross-unit route) is named, the Whisper forwards no sibling-written path text, and the optional G1 arm `AN` and its limitation sentence are recorded in the release decision.
- [ ] Founder answers to the open questions (T001).
- [ ] ADR proposal review disposition now and adoption with the G1 outcome (T002).
- [ ] G1 proposal consistency review (T004) and G1 frozen, run, reported and dispositioned (SPEC-057 T033 to T036).
- [ ] Guard probes GP-1 to GP-5 authorized by the founder, launched by the orchestrating session, recorded or listed as unobserved (T005 to T009).
- [ ] Unreleased engineering candidate implemented at a recorded commit for G1 arm A3 (T010 to T021, T023 to T025).
- [ ] Release decision recorded; package build, recipe, independent review and closure (T022, T026 to T028), only if GG (with GA) permits and the ADR is adopted.

Checked entries record document properties only.
