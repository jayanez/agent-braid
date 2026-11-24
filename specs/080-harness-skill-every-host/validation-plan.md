# SPEC-080: Validation plan

Status: draft; no procedure has obtained evidence. Each procedure records the exact
candidate commit, input hashes, command, exit, outcome and limits. Passing checks do
not prove safety or utility and are not approval.

| Procedure | Scenario | Method | Pass | Negative control / failure |
|---|---|---|---|---|
| procedure_001 | SC-001 | owner review record (T001) and Codex review triage (T002) | OD-1 to OD-7 decided or deferred; ADR 0044 accepted or rejected; every finding triaged | review treated as approval of an unimplemented candidate; a finding dropped without reason |
| procedure_002 | SC-002 | `tests/test_harness_skill.py` frontmatter and hash checks on a built plugin (T004, T005) | four keys only; name matches directory; same SHA-256 in three layouts | fixture with `allowed-tools` or a renamed directory still passes |
| procedure_003 | SC-003 | static extraction of commands from the skill text (T004) | extracted set equals the eight read commands; "experimental" and `executionAuthorization` present | `prepare` or `recover-inspect` inserted and the test still passes |
| procedure_004 | SC-004 | checklist review plus static test of decline and untrusted-data rules (T003, T004) | every forbidden effect has a decline line | a decline line removed and the test still passes |
| procedure_005 | SC-005 | `check_package_names` and plugin tests on a fresh build, and the loader tests (T005, T014) | exactly eight skills in every layout; each carries `metadata.license` and no top-level `license` | build with seven or nine skills accepted; a top-level `license` or missing `metadata.license` accepted |
| procedure_006 | SC-006 | host registry tests (T006) | `opencode` present, unqualified, not lifecycle-supported; Claude and Codex gate results unchanged on existing fixtures; importer table recorded; pre-change hook records verify | lifecycle install for `opencode` accepted; a `v0.1` record rejected or silently upgraded; an OpenCode hook record accepted |
| procedure_007 | SC-007 | one-command OpenCode observation in a temporary home (T007), then profile tests on its fixtures (T008) | written shape is the one the observed version reads and that version lists the installed server, or a stable refusal (`opencode-acceptance-unobserved` when acceptance is not observable); unowned keys untouched | an unobserved shape written; user configuration read or changed |
| procedure_008 | SC-008 | held-out set, REQ-008 scoring rule and retry message frozen by hash before any skill text (T009), automated driver per host (T010) | OD-3 target met per host; Wilson 95 % intervals and failure signatures recorded | set edited after a result is seen; a prompt sharing five consecutive words with `SKILL.md`; an unobservable attempt scored valid; a forbidden-effect prompt answered by running the effect |
| procedure_009 | SC-009 | telemetry test with a temporary store (T011) | no flag without a request; counts match calls with one; no record, path, hash or argument stored | the skill adds `--telemetry local` unasked |
| procedure_010 | SC-010 | release decision record (T012), docs check (T013) and publication record (T015) | each gate condition cites evidence; docs match the outcome | release with a failing condition; docs claim a skill that did not ship; publication before T013 |
