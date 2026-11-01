# SPEC-066 research

Sources were read on 2026-11-01. Upstream numbers are reports, not reproductions;
nothing here ran an upstream model. Repository facts were read from the working tree
at `develop` `6f2e795c`.

## The 2026-11-01 audit in brief

Full record: [completeness audit](../../docs/system-one/addenda/completeness-audit-20261101/README.md).
The decision it led to: [founder decisions 2026-11-01](../../docs/development/FOUNDER_DECISIONS_20261101.md).

| Finding | Consequence for SPEC-066 |
|---|---|
| S1.0–S1.4 (GitHub #13–#17) were closed on 2026-10-31 by the founder decision "Cerrar como diferido"; 45 issues closed as `COMPLETED` (about 22 with code from PRs #334, #373 and #655, about 23 on documents or historical records, none delivered in S1.2); 43 open S1 issues sit in Deferred (#24) | The milestone state is not evidence of delivery; S1.5 reuses the open issues instead of creating parallel ones |
| About 4,360 lines of `agent_braid/system_one*.py` and `mcp_advice.py` are on `develop` with no product callers; the only entry point is the opt-in `agent-braid system-one` command over synthetic fixtures; `analyze_with_advice`, `verify_candidates_with_advice` and `select_ready_rank_hint` have no source callers | Wiring is the missing piece; S1.5a adds the first caller, in shadow only |
| `BACKEND_ID = "stdlib-rule-fixture-v1"`, calibration is the constant `absent`, the strict policy always abstains | The S1.5a answer is a constant abstention; a real answer needs S1.5c–d |
| Telemetry cannot observe System One; real-use sources show zero System One invocations against 44 product calls (CLI `analyze` 4, `analyze-git` 8; MCP `analyze-work` 24, `analyze` 2, `execute` 2, `prepare` 2) | Use needs its own observation channel: the episode store, separate from the aggregate-only telemetry |
| 21 studies, mostly run by the Codex coordinator, ended as engineering and mostly negative scientifically; SPEC-029 T009 never ran; every study keeps `humanAcceptance: pending` | No prior result supports H-S1; S1.5a claims nothing |
| The reopen condition depends on RF-T03, RF-T04 and RF-T05, which have no owner; SPEC-029 required two blind human reviewers, which a one-person project cannot supply | REQ-101 admits owned sources; REQ-103 replaces the two-reviewer rubric with observed outcomes plus a sampled adjudication, reported as a limitation |
| README and RESUMPTION are stale (open milestones, local Codex checkouts) | T002 refreshes them |

The useful question follows from the audit. System 2 is exact and cheap, so a model
that repeats it has no value. System One earns its cost only where System 2 is
undetermined, which today means `unknown` pairs. Their ground truth arrives later as
an observed outcome of the owner's own work.

## Repository facts reused

| Fact | Source | Use |
|---|---|---|
| Pair classification (`independent-candidate`, `ordered`, `conflicting`, `unknown`), `sharedResources`, `reasons`, `constraints`, `evidence.coverage`, `evidence.ruleSet`; report `analyzer` and `summary` | `agent_braid/analysis.py` (`analyze`, `_interaction`) | episode pair fields and the reason table |
| The report lists per-operation resources but not effect kinds; kinds exist only in the request records (declared, inferred, observed channels) | `agent_braid/analysis.py` (`analyze`, `_effect_map`) | `effectKinds` is `null` in v0.1; request-derived kinds ship in episode v0.2 (T022) |
| Large results come back as an `evidence-artifact-reference`, and a Git replay `analyze` result has no interaction report | `agent_braid/tooling_mcp.py` (`_envelope`, `invoke`) | the observer resolves the retained artifact and treats a report-less result as a no-op |
| The MCP adapter admits at most 32 operations, so at most 496 pairs per call | `agent_braid/tooling_mcp.py` (`MAX_OPERATIONS`, `_validate_operation_bounds`) | the 64-pair cap bites from 12 operations (66 pairs) |
| `ToolingService.invoke` builds the envelope and, under telemetry, reads `result.get("report", result)` for `analyze` and `analyze-work` | `agent_braid/tooling_mcp.py` | wiring point and report access |
| Telemetry path rules: canonical, no symlinks, outside repositories, owner-only, owned, one hard link, fail-closed busy store | `agent_braid/tooling_telemetry.py` (`_path`, `Store._connect`) | episode store safety |
| Registry schema has a strict key set `{schema, telemetry, workspaces}`; `configuration_digest` hashes consent and normalized rows; `plan_setup` previews and `apply` is digest-bound | `agent_braid/plugin_registry.py` | optional `systemOne` member that leaves bytes and digest unchanged when absent |
| `PluginRouter.status` reports `telemetry: {configuredMode, activeMode, retentionDays, automaticUpload}` from a connection snapshot | `agent_braid/plugin_mcp.py` | `systemOne` block |
| `BACKEND_ID`, `MODEL_MANIFEST` and `capabilities()`; the rule backend answers only from hand-written `ruleAnswers` | `agent_braid/system_one.py`, `agent_braid/system_one_backends.py` | pinned identity; the reason shadow does not call `evaluate` in S1.5a |
| The `system-one` command returns before any `observe` wrapper; `observe` takes `(mode, surface, operation)` | `agent_braid/cli.py`, `agent_braid/tooling_telemetry.py` | `--telemetry` and the `system-one` operation |
| Validation rule `system-one-core` already covers `agent_braid/system_one*.py`, `cli.py` and `tests/test_system_one*.py` | `scripts/validate_change.py` | T019 |
| Real-use sources and receipt rules | `docs/development/REAL_USE_EVIDENCE.md` | SC-006 |
| Tracking is per spec, not per task: `github-tracking.json` assigns one milestone to each spec | `docs/development/github-tracking.json`, `scripts/sync_github_tracking.py` | T003 task-level override |

## Laya and Jev: design references only

Owner direction (2026-11-01, binding): Agent Braid builds its own, fully native layer-1
decision system. Laya and Jev are design references only: their ideas are re-implemented
by us, and nothing from them is used underneath (no service, no model, no backend, no
pretrained encoder, no weights). The table below lists which ideas are re-implemented
natively and why; "Adopt" means the idea, never the code or the model.

Survey: [reference analysis, 2026-11-01 update](../028-system-one-core/reference-analysis.md).
Boundary: [ADR 0034](../../docs/adr/0034-system-one-shadow-advisory-boundary.md).

| Capability | Source | Decision | Requirement |
|---|---|---|---|
| Pinned, versioned identity; floating alias drifts (`jev-latest`) | Jev, Laya checkpoint names | Adopt: backend ID and manifest digest in every episode; mismatch is refused | REQ-007, REQ-203 |
| Tri-state `passed / abstained / unevaluated`, echoed threshold, per-bucket thresholds | Laya | Adopt in S1.5c | REQ-201 |
| Act-above and ask-below thresholds scaled with risk | Jev | Adopt as risk-scaled thresholds; no learned act head | REQ-201 |
| Two confidence signals (entropy and maximum probability), per-band temperatures | Laya | Adopt, named by formula, never called accuracy | REQ-202 |
| Batched questions over one state, bounded batches of states | Jev, Laya | Adopt in S1.5c with per-question isolation | REQ-204 |
| Option-order rotation and equivariance reporting | Laya | Adopt in S1.5c; first-option bias is a documented Jev failure mode | REQ-205 |
| CI evaluation gate with a committed baseline | Laya (`laya-evals`) | Adopt in S1.5c | REQ-206 |
| Local checkpoints under Apache-2.0 (Laya, Von and other replicas) | Laya, Von | Not adopted: no third-party model, backend or pretrained encoder, ever. Replaced by a native stdlib model (calibrated logistic regression or boosted trees) trained on the owner's own work and compared with rules and the SPEC-019 linear model | REQ-301 |
| Hosted inference | Jev | Excluded permanently: the state leaves the machine and billing is per token; no external service of any kind (owner direction 2026-11-01) | none |
| Delete or skip by score | design notes on Jev use | Not adopted: a score never removes an item | ADR 0034 item 5 |
| Learned act/defer head | Laya | Not adopted: its reported signal was weak | ADR 0034 item 7 |
| Silent truncation, fail-open timeouts, floating aliases | Laya `predict_long`, SynapsCLI note | Not adopted: refuse or report | ADR 0034 |

Upstream numbers (for example Laya refit ECE 0.466 to 0.081, zero-shot accuracy 0.362
against a 0.461 majority baseline) are why S1.5d fits and calibrates on the owned
corpus instead of trusting any shipped confidence; no pretrained checkpoint is used. They are not Agent Braid results.

## Notes on the specification and contract

Found while planning. Each note is marked with its state after the specification and
contract were updated on 2026-11-01; the owner still confirms the whole at T001.

1. **Effect kinds are not in the report.** The report lists resources only, so the
   episode records `effectKinds` as `null` for both kinds. *Resolved in spec/contract
   (2026-11-01):* the contract makes `effectKinds` always `null` in v0.1 and reserves the
   shape. The owner then decided (R11, R12) that episode v0.2 ships with S1.5a and
   reads per-side kinds from the request records (T022).
2. **Dropped pairs bias the DP-1 share.** Pairs beyond 64 are dropped in report order,
   so a share over recorded pairs would be biased. *Resolved in spec/contract
   (2026-11-01):* the episode carries `classificationCounts` from the report summary, and
   the report computes `unknownShare` over all analysed pairs (`pairsAnalysed`), not only
   the recorded ones.
3. **`store-unavailable` cannot be recorded in the store.** *Resolved in spec/contract
   (2026-11-01):* the contract marks the reason as reserved; refusals and errors before
   storage exist only as in-memory counts.
4. **No success criterion for REQ-006, REQ-007 and REQ-008.** *Resolved in spec
   (2026-11-01):* SC-007 to SC-009 cover them; procedures 007–009 map to them.
5. **The report has no contract.** *Open:* REQ-005 now lists the report fields, but
   there is no `contracts/report-v0.1.md`; a contract file would settle the exact shape.
6. **REQ-003 lists a read-version flag** that the pair object does not have.
   *Resolved in spec (2026-11-01):* REQ-003 now names `read-version` as a reason code.
7. **SC-003 says "timing within budget".** Python cannot pre-empt a blocking write.
   *Resolved in spec (2026-11-01):* REQ-004 states that the 50 ms budget is a work
   budget checked between stages and does not bound a filesystem write. SC-003 keeps its
   short wording.
8. **Contract bounds exceed the reachable range.** `operationCount` up to 64 and
   `pairCount` up to 2016 are core limits; the MCP adapter admits 32 operations and 496
   pairs. *Open:* the contract notes the adapter limit of 32 for `operationCount` only;
   the 496-pair surface bound is not stated. Harmless.
9. **`plugin-status.systemOne.store` had no defined value.** *Resolved in spec
   (2026-11-01):* REQ-008 defines `store: {location, present}`; `location` shows the
   default path and `present` is a boolean.
10. **Existing issue numbers.** The brief for this track listed #322, #323, #324, #326
    and #328 for SPEC-033 T002, T003, T004, T006 and T008. Reading the issues shows those
    numbers are T001, T002, T003, T005 and T007. The correct numbers are #323, #324,
    #325, #327 and #329. *Resolved (2026-11-01):* the drafts use the corrected numbers.

## Alternatives and non-claims

- Retire System One: remains the outcome if the shadow period shows no usable signal
  (ADR 0034).
- Model-first: rejected; no owned population exists without episodes.
- Advise immediately: rejected; no calibration, no pinned backend, no outcomes.

Non-claims for S1.5a: no accuracy, calibration, utility or speed claim; no evidence
about H-S1; no statement that the DP-1 opportunity share is large (it is the first
thing the report measures); no human, founder or scientific acceptance.
