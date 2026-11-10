# SPEC-071: Lightning rollouts and verifiable reward

**Milestone:** BL.1 — Lightning rollouts and verifiable reward (GitHub milestone
created by the reviewed tracking reconciliation after merge).

**Status:** draft. Owner decisions L1–L5 of 2026-11-08 apply (see the
[program](../070-braid-lightning-foundations/program.md)). OD-1 and OD-2 are decided; T001 owner review
recorded on 2026-11-10 ([review](reviews/owner-t001-20261110.md)).
`human_review` is pending; this specification grants no execution authority.

## Purpose and scope

Braid Lightning needs a way to run the host models on a fixed prompt set, record
each rollout, and score it with a reward that a program computes. This
specification delivers that: a subscription-only rollout runner adapted from
upstream `controller/local_reconciler.py`, rollout hooks, and a verifiable reward
vector built on the SPEC-069 scoring rules. It is engineering, not a research
protocol; the optimization experiment is SPEC-072.

In scope:

- `agent_braid/lightning_hosts.py`: host argv, transcript parsers, OS sandbox,
  isolation probe and leak guard extracted from `scripts/spec069_native_runs.py`,
  which keeps its behaviour and tests;
- `agent_braid/lightning_runner.py`: subprocess rollouts with timeouts, process
  tree kill, `parallel` default 1, records written through the SPEC-070 store;
  subscription route only;
- `agent_braid/lightning_hooks.py`: `on_rollout_start`, `on_trace_end`,
  `on_rollout_end`;
- `agent_braid/lightning_reward.py`: the reward vector (schema validity, D4
  first-attempt and within-retry success, canary hits);
- anti-reward-hacking controls: hidden `.git`, network egress denied, canaries,
  frozen held-out hash check;
- CLI `agent-braid lightning run --dry-run|--fake-hosts`, `status`, `report`;
- one real baseline run through the subscription route.

Exclusions:

- Optimization algorithms and candidate generation (SPEC-072); promotion
  (SPEC-073); content-bearing traces (SPEC-074); dataset export (SPEC-075).
- Any paid API route, any `*_API_KEY`, any LLM judge in the reward.
- Codex as a rollout host (the configuration admits `claude-code` and
  `opencode` only).
- Any change to `analyze-work` semantics, the SPEC-069 prompt sets, FREEZE or
  scoring rules.
- Starting runs from the MCP server.

## Authorities

Constitution clause zero and Articles 12, 13, 14, 19, 20 and 23;
[GOVERNANCE.md](../../GOVERNANCE.md);
[claim discipline](../../docs/theory/CLAIM_DISCIPLINE.md);
[ADR 0021](../../docs/adr/0021-codex-claude-tooling-integration.md) (EUR 0
spend); [ADR 0034](../../docs/adr/0034-system-one-shadow-advisory-boundary.md)
(System One advisory boundary); [ADR 0039](../../docs/adr/0039-braid-lightning-boundary.md) (Braid Lightning boundary, accepted
2026-11-08) and [ADR 0040](../../docs/adr/0040-braid-lightning-mit-vendoring.md) (MIT vendoring into AGPL,
accepted 2026-11-08).
Precedents: [SPEC-049](../049-harness-evaluation-learning/spec.md) (human-only
promotion, budget stops), [SPEC-069](../069-aim-request-authoring/spec.md)
(driver, prompt sets, D4, T010 baseline),
[SPEC-070](../070-braid-lightning-foundations/spec.md) (schema, configuration,
store). Research basis:
[SPEC-070 research](../070-braid-lightning-foundations/research.md) and
[research.md](research.md).

## Clarifications

Owner decisions L1 (subscription route, EUR 0), L2 (first target is the
`analyze-work` authoring guidance, verifiable reward), L4 (naming) and L5 (full
definition now) apply. L3 (weight RL deferred) bounds this spec: nothing here
trains weights.

Design decisions recorded here:

- **R1 — Reward is a vector, not a scalar.** Components are reported
  separately; any scalar used by SPEC-072 is a declared function of the vector,
  recorded with the run.
- **R2 — D4 is reused, not redefined.** `score_case` and `wilson_interval` from
  `scripts/spec069_scoring.py` are called as frozen by
  `specs/069-aim-request-authoring/prompts/FREEZE.json`; the reward module checks
  the scoring file hash before use.
- **R3 — Extraction keeps the driver stable.** `scripts/spec069_native_runs.py`
  imports the extracted functions; its CLI, outputs and `KEY_SPECS` behaviour
  are unchanged. The Lightning runner never uses `KEY_SPECS`.
- **R4 — Quota is the budget.** The real budget is the subscription 5-hour and
  weekly windows. Stops reuse the `harness_hosts._BUDGET_STOPS` names.

Open decisions:

- **OD-1 — Subscription credential (decided 2026-11-08: OAuth token from the environment).** The owner chose that the runner accepts `CLAUDE_CODE_OAUTH_TOKEN` (and the OpenCode equivalent) read from the operator environment only, never written, for disposable profiles ([founder decisions](../../docs/development/FOUNDER_DECISIONS_20261108.md), decision 4). Original question: whether the runner may accept
  `CLAUDE_CODE_OAUTH_TOKEN` (and the OpenCode equivalent) from the operator's
  environment as the subscription credential for disposable profiles, or must
  rely only on an existing host sign-in. Either way the value is read from the
  environment only and never written. Owner decision; blocks T012.
- **OD-2 — OpenCode subscription evidence (decided 2026-11-10: refuse when unverified).** The owner chose that
  OpenCode runs only when it reports a subscription credential source; it currently reports none, so it is a
  declared limit (`route-unverified`) and BL.1 can close with Claude Code. Original question: which field of the OpenCode stream
  establishes the key source; if none exists, the runner records `unverified`
  and refuses (REQ-004). Decided after T003 research.

## Requirements

- **REQ-001 — Owner review.** The spec, plan, contracts and OD-1 are reviewed
  by the owner before T012; the review record names the frozen commit.
- **REQ-002 — Host extraction.** `lightning_hosts` provides `Profile`,
  `HostConfig`, `OsSandbox`, `probe_isolation`, `guard_leaks`, `Secrets`,
  `prompt_argv`, `parse_claude`, `parse_opencode`, `run_process` and
  `kill_tree` with the same behaviour as before extraction; the existing SPEC-069
  driver tests and `--fake-hosts` self-test pass unchanged, and the driver's
  evidence bytes for a fixed fake run are identical before and after.
- **REQ-003 — Runner.** `lightning_runner` runs one rollout per (prompt,
  repetition, host) as a subprocess in a disposable profile, enforces
  `rollout.timeoutSeconds` and `rollout.maxTurns`, kills the whole process tree
  on timeout or interrupt and verifies no leftover process, runs at most
  `rollout.parallel` rollouts at once (default 1), follows the SPEC-070 state
  machine, and writes each `braid-lightning-rollout/v0.1` record (owned by
  `agent_braid/lightning_schema.py`, unchanged) and one
  `braid-lightning-attempt-result/v0.1` record per attempt (new store kind
  `result`) through `lightning_store`.
- **REQ-004 — Subscription only.** Before launch the runner refuses
  (`paid-route-refused`) if the child environment contains any variable whose
  name ends in `_API_KEY`, or any of `ANTHROPIC_AUTH_TOKEN`,
  `ANTHROPIC_BASE_URL`, `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX`.
  After launch it records the host-reported `apiKeySource`. A missing
  `apiKeySource` ends the rollout as `route-unverified` and stops the run. The
  value `oauth` is accepted. The value `none` is accepted only as the SPEC-069
  fixture assumption, pending T003 evidence of what a subscription sign-in
  reports; any other value outside
  `harness_host_claude.SUBSCRIPTION_KEY_SOURCES` ends the rollout as
  `route-unverified`. Every attempt-result record carries `keySource`.
- **REQ-005 — Credential handling.** Depending on OD-1, the runner passes the
  subscription credential from its own environment to the child environment
  only; the value is registered with `Secrets` and never appears in any file,
  record, log or evidence (secret scan over the run directory); its presence is
  recorded as a boolean.
- **REQ-006 — Quota and budget stops.** The runner stops without retry when the
  host reports a window limit, mapping it to a name in `_BUDGET_STOPS`
  (`five-hour-headroom`, `weekly-stop`, `window-reset`, `window-reset-imminent`),
  or when `budget.maxRollouts` is reached (`unit-cap`); the stop name and the
  completed count are recorded and `status` reports them. A quota or budget
  stop ends the run; it resumes the same run id only by an explicit
  `agent-braid lightning run --resume <run-id>`, never automatically.
- **REQ-007 — Hooks.** `lightning_hooks` provides `on_rollout_start`,
  `on_trace_end` and `on_rollout_end` with upstream ordering; a hook exception
  is recorded and fails the rollout, never the store; hooks receive read-only
  records.
- **REQ-008 — Reward vector.** `lightning_reward` computes, per rollout, the
  vector in [contracts/reward-vector.md](contracts/reward-vector.md):
  `schemaValid` (via `agent_braid.analyze_work_schema` declared schema),
  `d4FirstAttempt` and `d4WithinRetry` (via `score_case`), `attempts`, and
  `canaryHits`. It is deterministic for equal inputs, uses no model call, and
  refuses if the scoring file hash differs from FREEZE.
- **REQ-009 — Anti-reward-hacking controls.** The model cannot read the
  workspace `.git`, the held-out file or the scoring source, and cannot reach the
  network, because every built-in file, shell and web tool is denied (the
  SPEC-069 allowlist leaves only Agent Braid MCP tools; the plugin itself needs
  `.git` for `git`-kind analysis); the OS sandbox additionally denies the real
  configuration and credential paths (it is not a network firewall); a canary token planted in non-target files is detected in tool
  calls or output and recorded as `canaryHits > 0`, which zeroes D4 for that
  rollout; the held-out set hash is checked against FREEZE before any held-out
  rollout.
- **REQ-010 — CLI.** `agent-braid lightning run` with `--dry-run` prints the
  planned rollouts, hosts and budget use without launching processes;
  `--fake-hosts` runs the full pipeline against the SPEC-069 fake hosts and
  labels evidence `pipeline-only`; `status` reports run state and stops;
  `report` prints per-host summaries with Wilson intervals. All outputs carry
  `executionAuthorization: false`.
- **REQ-011 — Replayable records.** Every attempt follows
  [contracts/rollout-record.md](contracts/rollout-record.md)
  (`braid-lightning-attempt-result/v0.1`, referencing the unchanged
  `braid-lightning-rollout/v0.1`) with candidate, prompt, transcript and reward
  hashes and the content-free parsed attempts (request envelope digests,
  refusal codes and `score_case` inputs). Replay recomputes the reward from
  those stored parsed attempts and yields byte-identical reward records.
  Replay from the transcript itself requires SPEC-074 consent `redacted`.
- **REQ-012 — Boundaries.** BL.1 code never calls `execute`, `recover` or grant
  paths, exposes no MCP tool, adds no runtime dependency, opens no listener, and
  every refusal uses the closed vocabulary in
  [contracts/refusals.md](contracts/refusals.md).
- **REQ-013 — Fake-host pipeline in CI.** A unit test runs
  `lightning run --fake-hosts` over the development set, with negative variants
  (planted `_API_KEY`, leaked secret, canary hit, straggler process, timeout),
  each producing its refusal or recorded outcome.
- **REQ-014 — Real baseline.** One real run of the T010 baseline guidance on the
  development set, three repetitions, in each host that has a subscription
  sign-in, yields a first-attempt success proportion inside the T010 Wilson
  interval [0.361, 0.698] per host
  (`evidence/native-runs-baseline-anthropic.json`) or outside it, with zero
  paid-route observations. Decided 2026-11-10: the requirement is that the run
  completes on the subscription route and reports the comparison; whether the
  proportion falls inside the interval is a finding, not a pass condition. Because the route, model and host versions differ from T010
  (API key route), the report is labelled `route-changed comparison`, not
  replication: it gives both proportions, both Wilson intervals and the
  route, model and version differences. A proportion outside the interval is
  reported as a difference, not hidden.

## Success criteria

Each requirement has one acceptance scenario (SC-001 to SC-014) in
`assurance.json`, with its procedure in [validation-plan.md](validation-plan.md).
Milestone exit: SC-013, SC-014 and SC-004 obtained, and OD-1 decided.

## Compatibility

Additive. `scripts/spec069_native_runs.py` keeps its CLI and evidence format;
its tests are the regression gate. No existing output changes.
`braid-lightning-rollout/v0.1` (owned by `agent_braid/lightning_schema.py`) is
unchanged. New records use the SPEC-070 store and the new identifiers
`braid-lightning-attempt-result/v0.1` (store kind `result`, added to
`lightning_store.KINDS`) and `braid-lightning-reward/v0.1`.
