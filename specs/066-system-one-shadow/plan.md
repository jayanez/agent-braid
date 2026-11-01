# SPEC-066 implementation plan

## Technical context and scope

- Python 3.12+, standard library only. The shadow module uses `json`, `os`,
  `fcntl`, `uuid`, `time.monotonic_ns` and `threading`. No network, no new
  runtime dependency, no import of `torch` or any model library.
- Tests: `unittest`, owned fixtures under `tests/fixtures/system_one_shadow/`.
- Scope is S1.5a as defined in [spec.md](spec.md): shadow mode for DP-1 (unknown-pair
  resolution) on the portable MCP `analyze-work` tool (the runtime `analyze` result carries
  no interaction report, so it yields no episode in v0.1). S1.5b–e are
  outline plans below; each needs its own plan and task review before any
  implementation starts.
- Inputs reused, not changed: the System 2 report (`agent_braid/analysis.py`),
  the telemetry path rules (`agent_braid/tooling_telemetry.py`), the plugin registry
  (`agent_braid/plugin_registry.py`) and the reference backend identity
  (`agent_braid/system_one.py`, `agent_braid/system_one_backends.py`).
- Order: the pure episode builder and its validator come first, because the episode
  contract is the privacy boundary. The store, wiring, consent, report and
  telemetry follow. The owner-run real-use check (SC-006) is last and is never
  implied by a passing test.

### Layout

```
agent_braid/
  system_one_shadow.py   constants, reason table, episode builder and validator,
                         pinned identity, EpisodeStore (append, retention, report,
                         purge), ShadowObserver (budget, containment, counters)
  tooling_mcp.py         ToolingConfig.system_one and a --system-one option of the
                         standalone entry point; ToolingService.invoke calls the
                         observer after the envelope exists (lazy import)
  plugin_registry.py     optional systemOne consent: decode, plan_setup, digest
  plugin_cli.py          plugin setup --system-one {off,shadow}
  plugin_mcp.py          PluginRouter passes the mode; plugin-status systemOne block
  system_one_cli.py      dispatch of report and purge; --telemetry on all subcommands
  cli.py                 parser entries for report, purge and --telemetry
  tooling_telemetry.py   OPERATIONS['cli'] gains 'system-one'; LIMITS text
docs/tooling/SYSTEM_ONE_SHADOW.md   user guide, privacy and non-claims
tests/test_system_one_shadow.py            builder, reason table, validator, identity
tests/test_system_one_shadow_store.py      store safety, caps, retention, report, purge
tests/test_system_one_shadow_parity.py     off/shadow byte parity, containment, budget
tests/test_system_one_shadow_consent.py    registry, setup, digest, plugin-status
tests/test_system_one_shadow_boundaries.py lazy import, no network, no authority
tests/fixtures/system_one_shadow/**
```

`system_one_shadow.py` is one module of roughly 400 lines. Splitting the store out
is deferred until S1.5b adds the outcome join, which needs a second file kind.

## Constitution check before research

| Article | Obligation | Design response |
|---|---|---|
| 0 | Hypotheses, analogy and evidence separated | H-S1 is a registered hypothesis; S1.5a produces only descriptive usage counts and tests nothing |
| 6 | Interaction properties drive scheduling | System One never reorders, filters or schedules in S1.5a; `unknown` stays `unknown` and serialized |
| 13 | Compatibility class on every analysis result; confidence is not a guarantee | the episode copies the System 2 class only as a closed vocabulary; the backend answer is `abstained` and carries no confidence |
| 17 | Yang–Baxter claim levels | not applicable: no Yang–Baxter claim is made. Claim labels follow [claim discipline](../../docs/theory/CLAIM_DISCIPLINE.md): engineering and hypothesis (H-S1); ADR 0034 records Laya and Jev as design references only (no third-party model or service) |
| 18 | Analogy is a hypothesis generator | no neuroscience or "System 1" claim; the name denotes a fast bounded decision path |
| 20 | Analysis and execution separate | `executionAuthorization` is the constant `false` in the episode and in the report; no execution path is added |
| 21, 22 | Practical value; mathematics not ornamental | the DP-1 opportunity share is the only utility figure; no accuracy or speed claim |
| 24 | Semantics precede production implementation | the episode contract and reason table are fixed before the observer is wired |

No MUST conflict found. SHOULD deviations: none recorded. The episode store holds
per-decision records, which SPEC-047 telemetry may not. ADR 0034 item 3 keeps them
in a separate store with a closed vocabulary, so the telemetry boundary is not
widened.

## Research, assumptions and alternatives

See [research.md](research.md). Assumptions:

- The portable MCP service stays the only wired surface; the CLI `analyze` and
  `analyze-git` commands are not instrumented (REQ-003 names MCP calls only).
- A shadow call after the envelope can add latency to the caller. The budget bounds
  the work done, not a stalled filesystem; Python cannot pre-empt a blocking write.
  The measured overhead (T021) is reported, not assumed.
- No empirical data is collected by S1.5a beyond descriptive counts. Labels,
  outcomes and the corpus belong to S1.5b.

Alternatives rejected:

- Store episodes inside the SPEC-047 SQLite telemetry store: breaks its aggregate-only
  boundary (ADR 0034 item 3).
- Run the shadow as a bounded synchronous call: superseded by owner decision OD-4
  (2026-11-01), which confirms a background single-slot worker that never blocks the
  caller. The race with the byte-parity test is handled by the worker having no
  access to the envelope (it receives a copy of the report only).
- Call `DecisionRuntime.evaluate` per pair: the reference backend only looks up
  hand-written `ruleAnswers` and cannot answer real pairs; the strict policy abstains
  without calibration anyway. The observer records the pinned identity and the
  constant abstention, and a real backend replaces that step in S1.5c–d.

## Design and compatibility

1. **Consent and config.** `ToolingConfig.system_one: str = "off"`; the
   constructor refuses values other than `off` and `shadow`. The registry gains the
   optional member `systemOne`. It is written only when its value is `shadow`, so a
   registry without it keeps its bytes and `configuration_digest` (SC-005).
   `_decode` accepts both key sets, `{schema, telemetry, workspaces}` and the same
   plus `systemOne`, with value `off` or `shadow`. `configuration_digest` adds
   `systemOne` to the hashed body only when it is `shadow`. `plan_setup` takes
   `system_one` (`None` keeps the current value, `off` removes the member), adds an
   effects line and sets `reconnectRequired`. `plugin setup --system-one` is
   accepted alone, like `--telemetry`. An older plugin build refuses a registry that
   carries `systemOne`, the same fail-closed behaviour the v0.2 migration notes; the
   setup preview says so.
2. **Wiring.** Per OD-4 the observer hands the finished report to one background worker with a single-slot queue and never waits (a busy worker drops and counts the report). `ToolingService.invoke` keeps its telemetry branch, then, when
   `config.system_one == "shadow"`, calls `shadow.observe(...)` with the finished
   envelope, the call name, the arguments and the config. The envelope object is
   returned unchanged. The call sits after the telemetry context closes, so the
   SPEC-047 duration histogram does not include shadow time. The import is lazy,
   inside the branch, so `off` never loads the module. Only `ok` envelopes of
   `analyze-work` with a System 2 report produce an episode; `analyze` (no report in its
   runtime result) and every other tool are no-ops.
   Two result shapes need care. A large result is returned as an
   `evidence-artifact-reference` and the report is read from the retained artifact
   bytes. A result without a `report` member, such as the Git replay form of
   `analyze`, is a no-op, not an error.
3. **Episode builder.** A pure function builds the object of
   [episode-v0.1](contracts/episode-v0.1.md) from the report
   (`result.get("report", result)`, as telemetry does) and from two call facts:
   the operation name and the analysis kind (`aim` or `git`). Rules:
   - `pairs` follow report order; at most 64 are kept (`pairsRecorded`), the total is
     `pairCount`.
   - `system2` is the pair classification; `system2Determinate` is false only for
     `unknown`; `dependency` is true when `system2` is `ordered`; `coverage` is the
     sorted `evidence.coverage`; `sharedResourceCount` is `len(sharedResources)`.
   - `constraints` are copied only if each value is in the closed set the analyzer
     emits: `preserve-dependency-order`, `serialize-or-isolate`,
     `serialize-unless-stronger-evidence`,
     `requires-execution-contract-before-parallelism`,
     `validate-read-versions-at-use`.
   - `effectKinds`: the report's `operations` list resources but not effect kinds, so
     the kinds are not derivable from the report and the value is `null` for both
     analysis kinds in S1.5a. The builder stays a pure function of the report. Reading
     kinds from the validated request records (declared, inferred and observed
     channels, as `analysis._effect_map` does) is deferred to S1.5b, and only if the
     DP-1 analysis shows the feature is needed; it would touch caller input and so
     needs its own privacy test.
     Owner decision R11/R12 (2026-11-01) supersedes the deferral: episode v0.2
     ([contract](contracts/episode-v0.2.md)) ships with S1.5a and adds per-side effect
     kinds from the request, resource classes, path depth, directory overlap and a
     separate per-repo salted hash field (task T022, REQ-003). v0.1 stays readable.
   - `classificationCounts` are copied from the report summary and sum to `pairCount`, so
     shares cover the pairs beyond the 64-pair cap.
   - `observedOutcome` is the constant `null`.
4. **Reason table.** Reason sentences map to codes by exact string equality. The
   sentences are taken from `agent_braid/analysis.py::_interaction`:

   | Sentence emitted by the analyzer | Code |
   |---|---|
   | An explicit dependency path orders the operations. | `dependency-order` |
   | At least one exact shared resource has a write-like effect. | `shared-write` |
   | At least one effect footprint is partial or unknown. | `partial-coverage` |
   | External, transforming, destructive, or unknown effects require adapter semantics. | `external-effect` |
   | Complete exact-resource footprints are disjoint. | `disjoint` |
   | Complete exact-resource footprints have no write conflict. | `shared-read-only` |
   | Read-version preconditions remain point-of-use obligations. | `read-version` |

   The table is versioned together with `RULE_SET` (`exact-resource-footprints-v1`).
   A sentence not in the table, or a `ruleSet` the table does not name, makes the
   episode `skipped` with reason `unmapped-reason`, and no free text is stored. A
   drift test scans the string literals appended to `reasons` in `_interaction` and
   fails when the analyzer gains a sentence the table lacks. The Git path builds its
   report with the same analyzer, so the table covers both kinds.
5. **Validator.** `validate_episode` enforces the contract: exact key sets, closed
   vocabularies, integer bounds, canonical form, no duplicate members, and no string
   outside the vocabularies other than `episodeId`, `day`, `backendId` and
   `manifestDigest`. The observer validates every episode before writing; a failure
   is `internal-error`, counted, not written.
6. **Pinned identity.** The module compiles in `EXPECTED_BACKEND_ID` and
   `EXPECTED_MANIFEST_DIGEST`. At observe time it reads the installed identity
   (`BACKEND_ID` and the digest of `MODEL_MANIFEST` from `system_one.py`). A
   difference records `refused` with `identity-mismatch`. A test asserts the compiled
   constants equal the installed ones, so a manifest change forces a deliberate
   constant update. With the reference backend and `calibration: absent`, the status
   is `abstained`, reason `calibration-absent`, `answers: null`.
7. **Store.** `EpisodeStore(directory=None)` defaults to
   `~/.local/share/agent-braid/system-one/`. Path rules are the telemetry rules:
   canonical path, no symlinks in any ancestor, outside any Git repository, owner-only
   mode, owned by the current user, regular files with one hard link. The module reuses
   the telemetry path checker rather than copying it, and a parity test runs the same
   hostile layouts against both. Operations:
   - `append(line)`: opens `episodes-<UTC date>.jsonl` with `O_APPEND | O_CREAT |
     O_NOFOLLOW`, mode `0o600`; takes a non-blocking advisory lock (a busy store
     refuses at once, no wait); refuses if the file size plus the line exceeds 4 MiB;
     writes the line with a single `write`; refuses unknown file names in the
     directory; prunes day files older than 29 days on every append and report.
   - A refusal increments an in-memory counter keyed by reason and returns. Nothing
     is raised into the caller.
   - An episode that cannot be stored cannot carry its own refusal, so `store-unavailable`
     is an in-memory counter reason only.
8. **Budget and containment.** The observer starts a monotonic clock, checks it before
   build, before serialization and before the write, and records `skipped` with
   `budget-exceeded` (a minimal episode with no pairs) once 50 ms elapse. A broad
   `except Exception` around the whole call counts `internal-error`; `BaseException`
   such as `KeyboardInterrupt` is not caught. The observer never mutates the envelope,
   the arguments or the report.
9. **Report and purge.** `report` reads the store with the same safety rules and the
   strict validator, skips and counts invalid lines, and never prints an episode
   body. JSON shape of `agent-braid-s1-report/v0.1` (spec REQ-005): `schema`,
   `retentionDays`, `days` and `totals` (episodes, operations, recorded System 2
   classes, all analysed pairs per class from `classificationCounts`, System One
   statuses), `pairsRecorded`, `pairsAnalysed`, `unknownPairs`, `unknownShare`,
   `invalidLines`, this process's refusal counts, `limits` and
   `executionAuthorization: false`. `unknownShare` is `unknownPairs / pairsAnalysed`
   over all analysed pairs, not only the recorded ones, and is `null` when no pair was
   analysed. The text format prints the same figures. `purge` deletes the episode files and the lock
   after a prompt, or with `--yes`; without a terminal it refuses unless `--yes` is
   given; it leaves unknown files alone and says so.
10. **CLI and telemetry.** The `system-one` parser gets a shared parent parser with
    `--telemetry {off,local}` (default `off`) for `capabilities`, `decide`, `report`
    and `purge`. `cli.py` wraps the dispatch in
    `observe("local", "cli", "system-one")` when the value is `local`. Exit codes 0 and
    1 (a valid abstention or deferral) are `ok`, 2 is `refused`, anything else is
    `error`. `OPERATIONS['cli']` becomes `('analyze', 'analyze-git', 'system-one')`;
    the classification metrics stay limited to the analysis operations. The LIMITS and
    `docs/tooling/TELEMETRY.md` coverage text name the new operation. Nothing else in
    the telemetry schema changes.
11. **plugin-status.** `PluginRouter.status` adds
    `systemOne: {configuredMode, activeMode, store, episodeRetentionDays: 30}`.
    `store` is `{location, present}`: `location` shows the default path and `present`
    is a boolean; the call never creates the directory and never reads episode bodies. `activeMode` is the connection snapshot,
    like telemetry.
12. **Validation profile.** `scripts/validate_change.py` already routes
    `agent_braid/system_one*.py`, `agent_braid/cli.py` and `tests/test_system_one*.py`
    to the `system-one-core` rule, and the remaining touched files to the fallback
    `full-tests`. T019 checks this with the planner, updates the rule boundary text to
    name the shadow, and adds a classification test only if a path escalates
    differently than expected.

Compatibility: additive. With `systemOne` absent or `off` there is no new import, no
new file, no registry byte change and no envelope change. The new CLI subcommands
and the `--telemetry` option are additive.

## Validation strategy

| Requirement | Scenario | Test module | Procedure |
|---|---|---|---|
| REQ-001 | SC-005 | `tests/test_system_one_shadow_consent.py` | procedure_005 |
| REQ-002 | SC-001, SC-003 | `tests/test_system_one_shadow_parity.py` | procedure_001, procedure_003 |
| REQ-003 | SC-002 | `tests/test_system_one_shadow.py` | procedure_002 |
| REQ-004 | SC-003 | `tests/test_system_one_shadow_store.py` | procedure_003 |
| REQ-005 | SC-004 | `tests/test_system_one_shadow_store.py`, `tests/test_system_one_cli.py` | procedure_004 |
| REQ-006 | SC-007 | `tests/test_tooling_telemetry.py`, `tests/test_system_one_cli.py` | procedure_007 |
| REQ-007 | SC-008 | `tests/test_system_one_shadow.py` | procedure_008 |
| REQ-008 | SC-009 | `tests/test_system_one_shadow_consent.py`, `tests/test_plugin_mcp.py` | procedure_009 |
| REQ-002, REQ-003 | SC-006 | owner-run receipt | procedure_006 |

REQ-006, REQ-007 and REQ-008 have SC-007 to SC-009 in the spec; procedures 007–009
cover them. Delivered tests so far live in one module, `tests/test_system_one_shadow.py`;
the other module names in this table are targets for the pending tasks.
Negative controls are listed per procedure in [validation-plan.md](validation-plan.md).
`assurance.json` holds planned evidence only until implementation.

## Constitution check after design

Unchanged: no MUST conflict. The design adds no execution path, no network use and no
change to any analysis, preparation or scheduling output. Article 13 risk (a score read
as a guarantee) is controlled by the constant abstention and the absence of any
confidence field in S1.5a. The new store is the only new persistent surface and is
bounded, private, structural-only and purgeable.

## Outline plans for S1.5b–e (blocked)

None of these starts before the S1.5a checkpoint (T031) and an owner review of the
stage's own plan.

**S1.5b — owned corpus.** An owner consent record admits the owner's own work as the only
training population (REQ-101), reusing the SPEC-051 pure validator (ADR 0026), restricted to
plugin-registered workspaces; any future repository needs the owner's express approval. A
separate outcome observer writes a joined record keyed by a random join key, not by any
input digest, from real-run signals: a runtime conflict, a merge conflict, a verify result
and the SPEC-059 ledger and SPEC-053 transcripts (REQ-102). A second label source is
git-history replay (REQ-104): pairs of real branches or commits of the registered
workspaces, the observed conflict from `git merge-tree`, reusing the SPEC-012 replay
planner. The label rubric is amended so observed outcomes are primary and an
owner-adjudicated random sample measures label noise (REQ-103). Feasibility gate: the
number of labelled DP-1 pairs, by class and by source, is shown before any fit. If the
yield is too low the track stays in shadow collection; the population is not widened
after labels are seen. It absorbs SPEC-029 T001–T003 and T008.

**S1.5c — reference-grade contracts.** Tri-state abstention with an echoed
threshold and per-bucket, risk-scaled thresholds fitted on a split disjoint from
evaluation (REQ-201); two named signals, normalized entropy and maximum probability
(REQ-202); drift demotion to `off` (REQ-203); batched questions over one state with
per-question isolation (REQ-204); option-order invariance by rotation with flip
reporting (REQ-205); a CI evaluation gate with a committed baseline (REQ-206). It
absorbs SPEC-029 T004 and T006 and SPEC-033 T004. These are native re-implementations
of ideas from the Laya and Jev design references.

**S1.5d — native learned model.** A native stdlib model module inside `agent_braid`
(`dependencies = []` in `pyproject.toml`; no numpy, no extra): calibrated logistic
regression or boosted trees over the structural features of episode v0.2
([contract](contracts/episode-v0.2.md)), with our own architecture, training and weights,
trained only on the S1.5b corpus (REQ-301). Temperature or isotonic calibration and
abstention thresholds are fitted on a separate calibration split. An ablation runs with
and without the per-repo salted resource hashes and keeps them only if they measurably
improve precision without degrading calibration. The model is compared with the rule
backend and the SPEC-019 linear model at a common risk budget, with the cost boundary
stated up front. No third-party model, backend, service or pretrained encoder is used
(owner direction 2026-11-01), so no dependency or licence ADR is needed. A NO-GO
verdict on H-S1 is a valid and recorded outcome. It absorbs SPEC-029 T005 and T007,
and SPEC-031 T008; SPEC-029 T009 and SPEC-030 T009/T013 (Laya reuse/comparison) are
superseded by the native-only direction.

**S1.5e — go/no-go.** Per decision point, an owner decision on recorded shadow
evidence moves `shadow` to `advise`, with an immutable promotion registry and an
atomic rollback to `off` (REQ-401). It absorbs SPEC-033 T002, T003, T006 and T008.
`advise` may only reorder or annotate. A score never removes an item.

## Human review and unresolved decisions

All decided by the owner on 2026-11-01
([owner-review-20261101.md](owner-review-20261101.md)). OD-1 was accepted as R1; OD-2,
OD-3 and OD-8 were accepted with it (the recommendations stand as written).

| ID | Decision | Owner's choice |
|---|---|---|
| OD-1 | Accept SPEC-066, this plan and the episode contract (T001) | **Decided: accepted** (R1) |
| OD-2 | Reuse the telemetry path checker versus copying it | **Decided:** reuse with a parity test; extract a shared helper later if a third store appears |
| OD-3 | Report JSON shape and `plugin-status.systemOne.store` representation | **Decided:** the shapes in design items 9 and 11 |
| OD-4 | Synchronous shadow call versus a background thread | **Decided: background single-slot worker** (R4); the request path never waits; a busy worker drops and counts the report |
| OD-5 | Move issues between milestones one by one | **Decided: task-level milestone override in the tracking source** (T003, R6) |
| OD-6 | Minimum duration and workload of the SC-006 real session | **Decided:** after merge, one week of normal work, the owner enables shadow with guidance (R13, R14); redacted receipt committed (R15) |
| OD-7 | Instrument CLI `analyze` and `analyze-git` as well | **Decided: deferred until after the first report** (R5) |
| OD-8 | A `--system-one {off,shadow}` option on the standalone `tooling_mcp` entry point | **Decided:** accepted, mirroring `--telemetry`; the plugin registry stays the consent path for the packaged plugin |

Implementation of S1.5a tasks may start. S1.5b–e tasks stay blocked until their own
plan review.
