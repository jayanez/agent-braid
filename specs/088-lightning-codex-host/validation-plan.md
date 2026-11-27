# SPEC-088: Validation plan

Status: draft; no procedure has obtained evidence. Each procedure records the
candidate commit, input hashes, command, exit, outcome and limits. Passing checks do
not prove that Codex works, is on a subscription route or meets any criterion, and are
not approval.

| Procedure | Scenario | Method | Pass | Negative control / failure |
|---|---|---|---|---|
| procedure_001 | SC-001 | owner review record (T001) | each open question decided or deferred; spec approved, amended or rejected | review read as approval of unwritten code or of a Codex run |
| procedure_002 | SC-002 | registry query and SPEC-087 guard test | `lightning-run` is claude-code, opencode, codex in order; no new exception file | a reordering or a new literal host list still passes |
| procedure_003 | SC-003 | key-set test of each feature-owned table | each key set equals its capability query | a key removed or added without the capability passes |
| procedure_004 | SC-004 | config validation with `optimizer.host` codex, opencode and claude-code | codex refused with config-enum, nothing launched; opencode passes config and is refused at launch as today; claude-code accepted | codex accepted as optimizer, or opencode refused at config time |
| procedure_005 | SC-005 | recorded fixture commands before and after, without codex | output bytes, digests and refusal codes identical except accepted-host text | the default `rollout.hosts` includes codex and the comparison still passes |
| procedure_006 | SC-006 | read every committed Lightning record and fixture; read a codex record | old records accepted and unchanged; codex record accepted; version string `v0.1` | a stored record rewritten or the version bumped |
| procedure_007 | SC-007 | fake Codex with a provider key, with no source, with the observed source and with another value | paid-route-refused; route-unverified; accepted only for the observed value | any other value or the absence of a source accepted |
| procedure_008 | SC-008 | run claude-code and codex where Codex reports no source; run claude-code with route-unverified | codex declared-limit, no run refusal, claude-code records normal; claude-code route-unverified still stops the run | a claude-code failure treated as a declared limit |
| procedure_009 | SC-009 | `parse_codex` and `tool_class` over recorded Codex streams; a stream with a denied tool and one with no model | tool calls, failure flags and classes equal the recording; denied classed denied; model unobserved | a guessed model or a denied tool classed as allowed |
| procedure_010 | SC-010 | `lightning run --fake-hosts` naming codex; the same stream with `fake_hosts` false | pipeline completes through the fake-only source, records labelled pipeline-only, no network or provider access; real verdict route-unverified | a record without the label, a traced network access, or the fake-only source accepted in a real run |
| procedure_011 | SC-011 | compute `h1_outcome`, the SPEC-049 pair and promotion inputs from a fake-host report with codex rows and from one with codex as a declared limit, and from the claude-code rows alone | all equal; `requiredHosts` is claude-code | codex rows change the outcome or `requiredHosts` |
| procedure_012 | SC-012 | real-host codex run invocation without setup consent (not under `--fake-hosts`); laboratory-only consent | consent-required; no content-bearing codex trace | a consent bypass or a trace written without consent |
| procedure_013 | SC-013 | export a codex rollout without a terms record; validate a synthetic record naming codex | terms-gate-missing; synthetic record validates and names no real provider | an export proceeds without a record |
| procedure_014 | SC-014 | plan and run naming codex on held-out, v2-feedback, v2-validation, v2-test, v3-test, v4-test and development | each non-development set refused before launch; development planned | a spent set reachable by codex |
| procedure_015 | SC-015 | `run --dry-run` naming codex; T011 decision record | `executionAuthorization` false, nothing launched; real run only with the owner's yes | a plan output that authorizes a run |
| procedure_016 | SC-016 | list the change set paths | no other spec, SPEC-069 to SPEC-073 driver, evidence, Constitution or replica changed | an edit to SPEC-087, SPEC-089, a closed spec or a driver |
| procedure_017 | SC-017 | inspect changed documentation and report text | no sentence claims a Codex result; LIGHTNING.md states route status and declared limit | a sentence that Codex meets D4 or is valid |
