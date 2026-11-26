# Issue drafts (published)

As of 2026-11-26, every draft that this file once held is a published GitHub issue in milestone S1.5 — System One shadow activation. The draft bodies were removed because the issues are now the source of truth: each issue carries its own `agent-braid-task-id` marker, state and body. Titles below are the published issue titles without the `[SPEC-NNN Tnnn]` prefix (otherwise identical to the former draft titles); read issue state on GitHub.

| Draft | Issue | Title |
|---|---|---|
| SPEC-066 | [#900](https://github.com/jayanez/agent-braid/issues/900) | SPEC-066: System One shadow activation and reference-grade decisions |
| SPEC-066/T001 | [#901](https://github.com/jayanez/agent-braid/issues/901) | Owner review of the specification, plan, episode contract and open decisions OD-1 to OD-8, including t... |
| SPEC-066/T002 | [#902](https://github.com/jayanez/agent-braid/issues/902) | Add the S1.5 track to ROADMAP, STATUS, the milestone index, docs/system-one/README.md and RESUMPTION,... |
| SPEC-066/T003 | [#903](https://github.com/jayanez/agent-braid/issues/903) | Support a task-level milestone override in the tracking source so the absorbed SPEC-029, SPEC-031 and... |
| SPEC-066/T004 | [#904](https://github.com/jayanez/agent-braid/issues/904) | After merge to develop, publish S1.5 tracking: audit scoped with --new-record-key for exactly the miss... |
| SPEC-066/T005 | [#905](https://github.com/jayanez/agent-braid/issues/905) | Freeze the specification candidate with python3 -m scripts.validate_spec_kit freeze specs/066-system-o... |
| SPEC-066/T010 | [#906](https://github.com/jayanez/agent-braid/issues/906) | Reason table and episode builder: pure functions that turn a System 2 report plus the operation name a... |
| SPEC-066/T011 | [#907](https://github.com/jayanez/agent-braid/issues/907) | Episode validator and privacy test: closed vocabularies, key sets, bounds, canonical bytes, duplicate... |
| SPEC-066/T012 | [#908](https://github.com/jayanez/agent-braid/issues/908) | Pinned identity: compiled backend ID and manifest digest, comparison with the installed identity, iden... |
| SPEC-066/T013 | [#909](https://github.com/jayanez/agent-braid/issues/909) | EpisodeStore: telemetry-equivalent path safety, private files, 4 MiB day cap, 30-date retention on acc... |
| SPEC-066/T014 | [#910](https://github.com/jayanez/agent-braid/issues/910) | Observer, budget and wiring: ToolingConfig.system_one, ShadowObserver with the 50 ms stage checks and... |
| SPEC-066/T015 | [#911](https://github.com/jayanez/agent-braid/issues/911) | Consent: registry systemOne member (decode, plan_setup, digest only when shadow), plugin setup --syste... |
| SPEC-066/T016 | [#912](https://github.com/jayanez/agent-braid/issues/912) | plugin-status systemOne block with configured and active mode, store state and retention; no directory... |
| SPEC-066/T017 | [#913](https://github.com/jayanez/agent-braid/issues/913) | system-one report (text and agent-braid-s1-report/v0.1 JSON) and purge with confirmation or --yes, ove... |
| SPEC-066/T018 | [#914](https://github.com/jayanez/agent-braid/issues/914) | --telemetry {off,local} on every system-one subcommand, the observe wrapper in cli.py, the system-one... |
| SPEC-066/T019 | [#915](https://github.com/jayanez/agent-braid/issues/915) | Boundary and validation-profile checks: off never imports the shadow module (subprocess sys.modules ch... |
| SPEC-066/T020 | [#916](https://github.com/jayanez/agent-braid/issues/916) | User documentation: docs/tooling/SYSTEM_ONE_SHADOW.md (what is recorded, what is never recorded, how t... |
| SPEC-066/T021 | [#917](https://github.com/jayanez/agent-braid/issues/917) | Overhead measurement: median and p95 of the shadow step for 2, 12 and 32 operations on the owner machi... |
| SPEC-066/T022 | [#918](https://github.com/jayanez/agent-braid/issues/918) | Episode v0.2 enrichment: extend the builder, validator and store to agent-braid-s1-episode/v0.2 ([cont... |
| SPEC-066/T030 | [#919](https://github.com/jayanez/agent-braid/issues/919) | Enable shadow on the owner machine with plugin setup --system-one shadow --apply, reconnect, work norm... |
| SPEC-066/T031 | [#920](https://github.com/jayanez/agent-braid/issues/920) | Pre-PR reviews (code review, quality, simplification), validate_change --profile pr on the stable cand... |
| SPEC-066/T032 | [#921](https://github.com/jayanez/agent-braid/issues/921) | Record obtained evidence in assurance.json, freeze, and owner review of the S1.5a closure, with the de... |
| SPEC-066/T101 | [#922](https://github.com/jayanez/agent-braid/issues/922) | Owner consent record that admits the owner's own work (episodes, real runs, and the SPEC-047, SPEC-053... |
| SPEC-066/T102 | [#923](https://github.com/jayanez/agent-braid/issues/923) | Outcome observer that joins DP-1 episodes with a later runtime conflict, merge conflict or verify resu... |
| SPEC-066/T103 | [#924](https://github.com/jayanez/agent-braid/issues/924) | Amended label rubric: observed outcomes primary, owner adjudication of a random sample for label noise... |
| SPEC-066/T104 | [#925](https://github.com/jayanez/agent-braid/issues/925) | Build the owned corpus with group split, near-duplicate audit, class and size coverage shown before an... |
| SPEC-066/T105 | [#926](https://github.com/jayanez/agent-braid/issues/926) | Owner adjudication of the random label sample. Dependencies: T103, T104. Evidence: owner record |
| SPEC-066/T106 | [#927](https://github.com/jayanez/agent-braid/issues/927) | Git-history replay labels: pair real branches or commits of the owner's plugin-registered workspaces,... |
| SPEC-066/T201 | [#928](https://github.com/jayanez/agent-braid/issues/928) | Tri-state abstention, echoed threshold and per-bucket, risk-scaled thresholds fitted on a split disjoi... |
| SPEC-066/T202 | [#929](https://github.com/jayanez/agent-braid/issues/929) | Two named confidence signals, normalized entropy and maximum probability, with stated formulas and no... |
| SPEC-066/T203 | [#930](https://github.com/jayanez/agent-braid/issues/930) | Drift demotion to off on a different or mixed backend identity until a new calibration is pinned, plus... |
| SPEC-066/T204 | [#931](https://github.com/jayanez/agent-braid/issues/931) | Batched questions over one state, bounded batches, per-question failure isolation, parity with unbatch... |
| SPEC-066/T205 | [#932](https://github.com/jayanez/agent-braid/issues/932) | Option-order invariance by rotation, equivariance tests and the adversarial conformance and sensitivit... |
| SPEC-066/T206 | [#933](https://github.com/jayanez/agent-braid/issues/933) | Evaluation gate in CI with minimum accuracy, maximum ECE, per-slice metrics and a tolerance against a... |
| SPEC-066/T301 | [#934](https://github.com/jayanez/agent-braid/issues/934) | Native model module inside agent_braid, standard library only (dependencies = []; no numpy, no extra,... |
| SPEC-066/T302 | [#935](https://github.com/jayanez/agent-braid/issues/935) | Calibration and abstention: temperature or isotonic scaling and abstention thresholds fitted on a cali... |
| SPEC-066/T303 | [#936](https://github.com/jayanez/agent-braid/issues/936) | Ablation with and without the per-repo salted resource hashes, then the registered comparison at a com... |
| SPEC-066/T401 | [#937](https://github.com/jayanez/agent-braid/issues/937) | Immutable promotion registry, shadow trace capture and retention reuse, and atomic rollback to off. Ca... |
| SPEC-066/T402 | [#938](https://github.com/jayanez/agent-braid/issues/938) | Paired shadow pilot with complete chain costs on the owner's work. Carries forward SPEC-033 T006 (#327... |
| SPEC-066/T403 | [#939](https://github.com/jayanez/agent-braid/issues/939) | Owner go/no-go per decision point and tracking reconciliation; advise only on a recorded go. Carries f... |

## Existing deferred issues to move to S1.5

Read-only check on 2026-11-01 with `gh issue view N --json number,title,state,milestone`: all 15 are open in milestone Deferred. Only the milestone changes; titles, bodies, parents and acceptance criteria stay. Moving an issue does not close, accept or authorize anything. It needs the task-level override of SPEC-066/T003, then the reviewed apply of T004.

| Issue | Task | Carried forward by | Current milestone | Target milestone |
|---|---|---|---|---|
| #285 | SPEC-029/T001 | SPEC-066/T101 | Deferred | S1.5 — System One shadow activation |
| #286 | SPEC-029/T002 | SPEC-066/T103 | Deferred | S1.5 — System One shadow activation |
| #287 | SPEC-029/T003 | SPEC-066/T104 | Deferred | S1.5 — System One shadow activation |
| #288 | SPEC-029/T004 | SPEC-066/T205 | Deferred | S1.5 — System One shadow activation |
| #289 | SPEC-029/T005 | SPEC-066/T302 | Deferred | S1.5 — System One shadow activation |
| #290 | SPEC-029/T006 | SPEC-066/T201 | Deferred | S1.5 — System One shadow activation |
| #291 | SPEC-029/T007 | SPEC-066/T302 | Deferred | S1.5 — System One shadow activation |
| #292 | SPEC-029/T008 | SPEC-066/T104 | Deferred | S1.5 — System One shadow activation |
| #293 | SPEC-029/T009 | SPEC-066/T303 | Deferred | S1.5 — System One shadow activation |
| #311 | SPEC-031/T008 | SPEC-066/T303 | Deferred | S1.5 — System One shadow activation |
| #323 | SPEC-033/T002 | SPEC-066/T401 | Deferred | S1.5 — System One shadow activation |
| #324 | SPEC-033/T003 | SPEC-066/T401 | Deferred | S1.5 — System One shadow activation |
| #325 | SPEC-033/T004 | SPEC-066/T203 | Deferred | S1.5 — System One shadow activation |
| #327 | SPEC-033/T006 | SPEC-066/T402 | Deferred | S1.5 — System One shadow activation |
| #329 | SPEC-033/T008 | SPEC-066/T403 | Deferred | S1.5 — System One shadow activation |

Correction to the requested list: the brief named #322, #323, #324, #326 and #328 for SPEC-033 T002, T003, T004, T006 and T008. Those issues are T001, T002, T003, T005 and T007. The matching issues are #323, #324, #325, #327 and #329, used above. #322 (T001, promotion criteria review), #326 (T005, rollback implementation) and #328 (T007, closure packet) stay in Deferred because the founder decision of 2026-11-01 lists only SPEC-033 T002, T003, T004, T006 and T008 as absorbed; the owner can add them at T001.

Stay in Deferred: the parents SPEC-028 to SPEC-033, SPEC-031 T001-T007, SPEC-030 and SPEC-032 tasks, SPEC-033 T001, T005 and T007, and every other open S1 issue.
