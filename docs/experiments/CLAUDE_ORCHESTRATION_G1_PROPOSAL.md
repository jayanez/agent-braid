# Proposed preregistration: M4.6 gate G1, Claude orchestration ownership evidence

**Status:** Proposed and not frozen. Nothing in this document authorizes a
workflow run, a concurrent agent, a session launch, a spend, a push or a remote
issue. Freezing is an explicit founder act (see "Freezing"). The exact
machine-readable inputs are in
[claude-orchestration-g1-inputs.json](claude-orchestration-g1-inputs.json); the
checker is `scripts/validate_claude_orchestration_g1_proposal.py`.

**Milestone:** M4.6, Claude Code dynamic workflows. **Hypothesis:**
[H-CW2](../../research/hypotheses/H-CW2-claude-orchestration-ownership.md).
**Owner of the gate:** SPEC-057. **Gated by this experiment:** SPEC-058 (opt-in
guard). **Not gated by it, but informed:** SPEC-059 (a sketch: notification
companion, opt-in push and the attributed-write ledger), which is additionally
blocked by gate G2 (the `specs/039` coordination contract).
**Integration comparator:** the SPEC-052 end-of-run gate where the surface has
one, defined per surface in "Surfaces" (not every surface has one). G0
(transcript evidence) is a separate, independent preregistration and is not a
prerequisite.

## Decision requested

Accept, amend or reject one preregistered experiment (gate G1) that screens three
separable propositions on real Claude Code runs: (a) declared ownership with
advisory pre-flight analysis and a declared-versus-observed envelope receipt
(SPEC-057); (b) epoch-stamped pull digests (the SPEC-057 notification default,
and the evidence that SPEC-059 would need); (c) an opt-in enforcement profile
compiled from the same ownership declaration (SPEC-058). If the founder freezes
it, the founder runs the arms below and the recorded results decide, per
proposition, whether the corresponding spec is released, narrowed or closed as
not adopted. G1 is a small, paired, partly designed screen. It is not a
prevalence estimate, a benchmark, a safety proof or a speed claim. At the
minimum counts and EUR 0 it is likely to end `inconclusive` for the guard (see
"Feasibility projection"); the founder is told that up front.

## Clarifications

Founder decisions of 2026-10-24 (round 2) that bind this proposal:

- **Staging.** Stage 1 (S1) runs first and on two surfaces only. The planned run
  count and every threshold are fixed before freezing. If the planned count
  cannot hold the minimums at EUR 0, the experiment is downgraded to
  observational before launch (see "Feasibility projection"). The remaining
  surfaces run only after a separate founder decision; otherwise they stay
  `not-claimed`.
- **CA1 stated limit.** CA1 asks only that a designed task set with a catch
  exist on at least 2 surfaces. That is an existence screen on designed overlap,
  not a rate and not evidence about natural conflicts.
- **GG.** The guard gate needs at least 1 claimed surface.
- **`/batch`.** Whether the pre-flight applies to `/batch` units is decided after
  the layout probe and before freezing; until then it is a pre-freeze binding.
- **A3 mechanism (blocker resolution).** SPEC-058 must be implemented as an
  unreleased engineering candidate, behind the G1 gate, before arm A3 can run. It
  is built from a recorded commit that is hashed in the manifest, is not
  packaged or published, and is installed by the founder as an explicit opt-in.
  Adoption or release happens only after GG passes and the guard ADR is adopted;
  the guard ADR proposal is reviewed now and adopted together with the G1
  outcome, not before it.
  The gate therefore governs release, not implementation, which removes the
  circularity of an arm that needs code the gate blocks. A hand-written throwaway
  hook was considered and not chosen: it would evaluate a different artifact than
  the one the gate decides about.
- **Notifications.** The default strategy is "Mailbox + Whisper": pull notices
  the orchestrator reads (the host already wakes the orchestrator at each
  linked-session turn end) plus `PreToolUse` additional context to the affected
  agent in its own session. A2 measures the Mailbox part; the Whisper part is
  exercised only inside the A3 candidate. "Megaphone" (monitor or channels) and
  "Doorbell" (a script posting data only to the orchestrator's own session
  messaging socket) are opt-in in SPEC-059 only, enabled only if G1 shows late
  notices with measurable harm (criterion CN2 below) and, for Doorbell, a
  verified transport after G2. Neither is an arm of G1.
- **Native controls.** The guard arms are compared with a native-controls-only
  arm `AN` (hand-written `permissions.deny` and sandbox write allowlist from the
  same ownership declaration) in stage 2. The comparison is descriptive and sets
  the release wording; if `AN` is not run, the limit is stated (see "Decision and
  kill criteria").
- **Settings precedence.** The most specific scope wins (conversation, then
  repository, then user), except that a `block` set at repository or user scope
  is a floor a conversation cannot lower. Settings are operator-owned.
- **Guard failure.** An internal error or timeout of the guard fails open: it is
  recorded as no-opinion, the event is logged, and the liveness attestation
  degrades to advisory. `ask` is kept only for undecidable paths in `block` mode
  until probe GP-2 is recorded.
- **Unattributed writers.** Writes by the orchestrator, a human or a shared tree
  are `unknown` by default; only an explicit declared exemption rule excludes
  them.
- **Article 13 classes.** The declared-versus-observed exact-path receipt is
  class 1 (syntactic). The pre-flight, the recovery report and the isolation
  audit are class 0 (heuristic). Every output states that it is not a guarantee.
- **Probes.** The orchestrator (the Claude main session) launches host probes
  HV-6 to HV-13 through workflows or derived sessions only after the founder
  authorizes each probe. Agents prepare log-only scripts. Evidence is pinned with
  the host version.
- **Not in G1.** No `PostToolUse` Bash observer. The attributed-write ledger for
  agent teams is decided after probe HV-L7; otherwise documentation and
  per-teammate checkpoints. G2 is decided after G1. Companion names and
  distribution are decided after G1. Interoperability is documentation now.
  Telemetry from G0 or G1 manifests is never collected.

## Question and claim labels

On real multi-worktree and shared-tree Claude Code runs, do declared ownership
and pre-flight analysis with a checkpoint receipt, and separately the opt-in
enforcement profile, prevent or catch integration failures earlier than the
baseline without destroying parallelism or creating false assurance?

- Hypothesis (H-CW2): yes, in the stated domain and per surface. Untested.
- Heuristic: a declared file-level footprint predicts integration hazards.
  Declarations are claims, not observations; a disjoint-file declaration does
  not imply a clean merge (disjoint-file textual conflicts are reported in the
  literature), so the pre-flight false-assurance rate is a primary metric.
- Analogy only: no braid or commutation claim is made by G1.
- Negative results are valid. Parallel runtime speedup is a recorded NO-GO
  (SPEC-021 G4, SPEC-022, SPEC-038); G1 makes no speed claim. Time and tokens are
  reported as cost only.
- Absence of a conflict in a run is not evidence of safety. A pass adopts
  nothing (see "Decision and kill criteria").

## Surfaces, population, sampling frame

All four surfaces decided for M4.6 are measured, each with its own minimum, and
each is claimed or dropped on its own:

| Surface | Unit under test | Isolation in the baseline | Integration comparator and catch kinds |
|---|---|---|---|
| `workflow-tracks` | tracks (agents) of a dynamic workflow, 3 or 4 per task set | worktree flag where the host option applies | the SPEC-052 end-of-run gate; stage order is checkpoint receipt, then gate. Kinds: `prevented`, `caught-earlier` |
| `linked-sessions` | sessions launched from another session (desktop session start, background or agent-view sessions) with cross-session messaging relayed by the orchestrator, 3 or 4 per task set | the host's own worktree dispatch where it applies, recorded per run | the SPEC-052 end-of-run gate, as above. Kinds: `prevented`, `caught-earlier` |
| `agent-teams` | teammates sharing one working tree, 3 or 4 per task set | none (shared tree) | no commit-stage gate exists on a shared tree, so there is no stage order; the comparator is the final-tree tests and the `lost-update` outcome. Kind: `prevented` only |
| `batch` | units of a `/batch` decomposition, 5 or 6 per task set | the host's per-unit worktrees; unit boundaries are the host's | undefined until probe HV-11 records the layout; the cell is `not-comparable` until then. Kind: `prevented` only, and only after HV-11 |

`caught-earlier` is defined only where a stage order against the SPEC-052 gate
exists, that is on `workflow-tracks` and `linked-sessions`. A stage 1 pair that
contains neither limits CA1 to `prevented`. On `agent-teams` every change on the
shared tree is an unattributed writer (`unknown`), so a per-unit
declared-versus-observed comparison is limited to what the host's tool records
attribute, and a receipt can be refused when its input exceeds the bound; such a
refusal is recorded as `receipt-unavailable`, counts as no hazard raised, and is
never an exclusion.

- **Scope:** Claude Code only. Codex, cloud sessions, Remote Control, other
  machines and VS Code are not covered and no claim extends to them.
- **Source and permissions:** repositories controlled by the founder, named in
  the run manifest at freezing (not named here; the repository binding is a
  required pre-freeze field). The founder's existing subscription at Sonnet and
  medium effort. No third-party repository, user or transcript is in scope.
- **Host verification first.** The host behaviours that the arms depend on are
  unverified or inferred today: plugin hooks firing inside workflow agents,
  `/batch` units and teammates; native permission deny rules and the sandbox
  write allowlist applying inside subagents and teammates; plugin MCP tools
  being available inside workflow agents; Task tools being present for task
  hooks; dispatched sessions reading their configuration; and the `/batch` and
  agent-view layouts. Each is a recorded observation with the host version
  (the inputs file maps each probe name to its HV or GP identifier, which is the
  join key for the receipt) before any arm that depends on it. A behaviour
  that is not observed means the dependent arm is not run on that surface and
  the surface is `guard-not-covered` or `not-claimed` for it. Nothing is assumed.
- **Task sets and strata.** A task set is the unit of pairing: one task
  decomposed into tracks by the founder before launch. Two strata are reported
  separately and never pooled for prevalence:
  - `natural`: task sets taken from the founder's own backlog by a pre-stated
    rule fixed in the manifest (the next open items, in identifier order, that
    touch at least two modules), decomposed into tracks before any Braid output
    is seen. No overlap is designed in. Used for the cost side: false-block
    rate, bypass rate, unnecessary serialization, false assurance, overhead.
  - `designed`: task sets written with a stated overlap type (same file, shared
    symbol, cross-file contract, shared resource such as a lock or generated
    file, new-file path collision, read-after-write stale read; each type at
    least once across the experiment). Used for the benefit side as an existence
    screen, and for the tamper negative control. Designed overlap makes the
    conflict rate high by construction and is a stated limit on
    generalization; it is never used to estimate prevalence.
- **Minimums:** per surface at least 3 eligible natural and at least 3 eligible
  designed task sets; at most 8 task sets started per surface so that ineligible
  ones can be replaced. A surface below its minimum is `not-claimed` for every
  gate. Design properties are recorded before launch and never assigned or
  changed after an outcome is seen.
- **Eligibility (all required):** the base tree passes the project tests; the
  run completes inside the protocol (no unplanned human edit of agent output);
  the host version did not change during the task set; no quota exhaustion. A
  worktree-surface track that does not commit is an `incomplete-track` outcome,
  not an exclusion (intention to treat, below). Exclusions are reported with
  counts: `base-tests-fail`, `flaky-final-tests` (the final test command gives
  different results in two executions), `workflow-aborted`, `quota-exhausted`,
  `host-version-changed`, `manual-edit-of-agent-output`.
- **Symmetric, pre-stated exclusion.** The exclusion list is fixed before
  freezing. An exclusion removes the whole task set from every arm (the pairing
  unit), never one arm of it, and is decided mechanically before any reference
  outcome is computed. A reason that depends on the outcome is not allowed. The
  report lists every excluded task set, the arm and reason, and the
  **excluded harm**: failures, deny events and false blocks that occurred in the excluded
  task sets before exclusion.
- **Intention to treat.** A treatment-induced non-commit or workflow stall is a
  failure of that arm and, when a deny preceded it, a false-block datum in
  CG2. It is never removed as `agent-did-not-commit`. A non-commit that occurs
  in `A0` as well is recorded as a failure in `A0` too.

## Arms

| Arm | Definition |
|---|---|
| `A0` | Baseline. Prompt partitioning per the host's published guidance (prose such as each agent owns different files), the worktree or isolation flag where the surface offers it, plus the integration comparator of the surface (the SPEC-052 end-of-run gate and `git merge-tree` where one exists, see "Surfaces"). Prompt templates are hashed before freezing. |
| `A1` | A0 plus the advisory pre-flight (declared ownership, pairwise verdict with coverage and unknown, isolation and base audit) before launch and the declared-versus-observed envelope receipt at each quiescent checkpoint (track completion or the orchestrator's explicit request). Advisory only: the orchestrator is free to ignore it. |
| `A2` | A1 plus epoch-stamped pull digests ("Mailbox"). A2 differs from A1 in cadence and reader, not only in rendering: a digest is produced at every orchestrator turn end (`linked-sessions`) or teammate idle event (`agent-teams`) and the orchestrator reads it before continuing, while A1 produces the receipt only at the checkpoints above. The cadence of each arm is recorded in the manifest and hashed. Pull only; no active push, no Megaphone, no Doorbell. |
| `A3a` | A2 plus the enforcement profile in `audit` mode, which records "would have blocked" and changes no behavior. |
| `A3b` | A3a with the profile in `block` mode. |
| `AN` | Native controls only (optional, stage 2). A0 plus a hand-written `permissions.deny` and sandbox write allowlist that the founder derives from the same ownership declaration; no pre-flight, receipt, digest or candidate. The rules are written and hashed before launch. Descriptive comparison with `A3b`; it has no threshold and sets only the release wording. |

`A3a` and `A3b` gate SPEC-058 only. Both run the unreleased SPEC-058
engineering candidate (see Clarifications) from a hashed commit, not a
throwaway script and not a released product. The candidate compiles the profile
from the same declaration; which output is used on a surface (native permission
deny plus sandbox write allowlist, the companion plugin `agent-braid-guard`
(working name), or the exported settings snippet) is decided by the
host-verification observations and recorded per run, and results are reported
per output. The product is evaluated only through this candidate. Hooks inside
the main plugin are rejected and are not an arm. The profile's output vocabulary
is no-opinion, ask, deny and additional context; it never returns allow and
never holds a grant. Mode default when enabled is `audit`. Agent Braid never
launches, messages as, resumes or authorizes any session, agent or team in any
arm; the founder (as orchestrator) does.

Stages: `S1` runs `A0`, `A1`, `A2` on two surfaces chosen and recorded in the
manifest before freezing, plus the null control below. `S2` runs on the same task
sets only after the founder reads the `S1` report and records a separate
decision; `S2` is never started implicitly, and does not start before the
unreleased candidate exists at a hashed commit. `S2a` runs `A3a` on every task
set; `S2b` runs `A3b` (and `AN` when run) only if the denominator projection in
"Feasibility projection" holds. `A3a` therefore always precedes `A3b`; since
`A3a` changes no behavior this order effect is recorded, not corrected. Each
task set is run in every arm of its stage, with 2 repetitions per task and arm,
in an arm order fixed by a recorded permutation seed in the manifest (the order
is permuted within `S1`, within `S2a` and within `S2b`). The repetition index
and permutation seed are the only controlled seeds: model sampling is not
controllable and is treated as noise, so a single run never establishes a
counterfactual. Each run starts from a fresh clone at the base commit.

**Null control and noise floor.** For one designed task set per claimed `S1`
surface, `A0` is run a second time (`A0n`, 2 repetitions, same protocol, no
treatment). Together with the two `A0` repetitions of every designed task set it
gives the pre-stated noise floor for CA1: the share of designed task sets on the
surface whose two `A0` repetitions disagree (one failure, one clean) and the
outcome of the `A0` against `A0n` pair, which must not look like a catch.

## Procedure per run

1. **Manifest first.** Before launch the founder records and hashes: run id,
   task set and stratum, overlap type (designed only), surface, arm, repetition,
   base commit, tracks, tool and host versions (Claude Code, Agent Braid commit,
   plugin version, model and effort), test command, and (A3) the enforcement
   output in use.
2. **Run.** The founder starts and approves the run on the existing
   subscription. Declarations for `A1` to `A3b`, and the `AN` rule files, are
   written before launch and hashed.
3. **Predict before reference.** For each task set, every declaration,
   pre-flight output, planted-overlap description and `AN` rule file is written
   and hashed before the first arm of that task set launches. The reference
   outcome of any run is computed, and released to the founder, only after every
   arm of the stage has finished for that task set. This limits, but does not
   remove, the founder's knowledge of earlier arms, which is stated as a limit.
   G1 measures the founder's declarations (recall and precision), not those of a
   model orchestrator or of the Claude session.
4. **Reference outcome.** Worktree surfaces (`workflow-tracks`,
   `linked-sessions`, `batch`): merge the track branches into a throwaway clone
   at the base commit in a serial order fixed in the manifest, then run the
   project tests twice; outcomes `clean`, `textual-conflict`, `semantic-failure`
   as in G0. The shared-tree surface (`agent-teams`): the final tree is tested
   twice and per-teammate writes are attributed from the host's local record of
   tool calls; outcomes `clean`, `lost-update` (two teammates wrote the same
   path and a hunk of the earlier write is absent from the final content) and
   `semantic-failure`. Write attribution from tool records cannot see
   shell-driven writes, which is recorded as a limit. A run is a reference
   failure when its outcome is not `clean`.
5. **Record aggregates** (see "Retention") and keep raw material private.

## Metrics

A "catch" is a paired counterfactual on one task set and one surface, never a
single run. All of the following hold:

1. `A0` is a reference failure in **both** repetitions (a majority of its
   repetitions).
2. The hazard in the treatment arm names the exact unit pair and at least one
   path that appears in the `A0` reference failure, and was raised and hashed
   before the failing stage.
3. Either the treatment arm is reference-clean in **both** repetitions
   (`prevented`), or, on `workflow-tracks` and `linked-sessions` only, it raised
   that hazard at a checkpoint before the SPEC-052 end-gate stage in every
   repetition in which the reference outcome failed
   (`caught-earlier-than-spec052-gate`, by stage order in the manifest).
4. The surface passes the noise floor: its `A0` repetitions disagree on at most
   one third of its designed task sets, and its `A0` against `A0n` pair is not a
   catch. A surface that fails the noise floor does not count toward CA1.

Under no treatment effect and independent runs with a failure probability q per
run, the chance of a catch on one designed task set against `A1` or `A2` is
0.07 at q = 0.3 and 0.11 at q = 0.5; of one on at least one of 3 designed task
sets, 0.19 and 0.29; and of CA1 on two surfaces, 0.03 and 0.09 (q = 0.2: 0.01).
CA1 is therefore weak evidence at its minimum size, and the report states
these numbers beside any CA1 pass.

1. **Conflicts prevented or caught earlier** than the SPEC-052 gate, per arm,
   surface and stratum, with the discordant task-set counts against `A0`.
2. **Parallelism retained.** Unnecessary serialization rate: tracks that the
   advice (or the founder following it) serialized or merged, as a share of
   tracks in task sets whose `A0` outcome was clean in every repetition. Also
   the share of tracks that stayed concurrent relative to `A0`.
3. **False-block rate** (`A3b`): denied operations later judged necessary for the
   task, over deny events; and the share of tracks with at least one false block.
   A treatment-induced non-commit after a deny is a false block (intention to
   treat). Deny events are reported by stratum.
   Adjudication is mechanical first (a denied path that the same track wrote in
   `A0` and that no sibling's `A0` conflict involved is a false block), and the
   residual cases are decided by the founder blind to the arm, with the count of
   residual cases reported.
4. **Bypass rate** (`A3b`): tracks with at least one deny in which the denied
   change reappeared by another route (shell write, interpreter write, tool
   outside the matcher), over tracks with at least one deny. Attempted and
   successful modification of the envelope, ledger, settings or hook paths are
   counted separately; the designed stratum includes tamper-invitation task sets
   as a negative control.
5. **Pre-flight false-assurance rate.** Natural-stratum task sets in which
   pre-flight flagged no pair (all pairs `independent-candidate`) and the
   reference outcome was a failure in at least one repetition of any arm, over
   natural-stratum task sets in which pre-flight flagged no pair. The task set is
   the unit: `A1` and `A2` share one declaration, and pairs and repetitions
   inside a task set are not independent. The Wilson 95% upper bound is reported
   beside every value.
6. **Declaration recall and precision** against observed writes (per task set,
   pooling its repetitions of `A1` and `A2`: the
   share of observed written paths that were declared, and the share of declared
   paths that were written), and observed-read recall reported descriptively
   (reads come from local tool records and are an agent's recorded intent).
7. **Pair unknown share** of the pre-flight verdicts, per task set.
8. **Enforcement liveness** (`A3a`, `A3b`): enforcement events observed over
   events expected, per surface and output, with a canary event injected per
   task set.
9. **Overhead as cost:** added orchestrator context tokens as a share of the
   matching `A0` median, digests per track, hook latency p50 and p95, added tool
   calls. Wall time and tokens are cost, never speed.
10. **Unattributed writers:** writes by the orchestrator, a human or a shared
    tree during a run are `unknown` by default and reported as unknown writers.
    They are excluded from declared-versus-observed scoring only by an explicit
    declared exemption rule recorded before launch.

Recovery (the interrupted-work report, REQ-007 of SPEC-057) is outside G1
evidence: G1 does not measure it, and no G1 result speaks to it.

## Preregistered thresholds

All values are proposed, are fixed before any data exist, and are the only
success criteria. Intervals (Wilson 95%) and discordant counts are description,
not inference. **The statistical unit is the task set** for CA1, CA3, CA4, CA6
and the guard rates that are not per deny event or per track; repetitions and
runs of one task set are never counted as independent units. A pass means only
that the criterion was not violated in the observed task sets, with the interval
reported; it is not a safety result.

### Gate GA, advisory core (arms `A1`, `A2`; informs SPEC-057)

Hard criteria (a failure here is a fail even if the benefit appears):

- **CA3 (screen, not a safety gate):** pre-flight false-assurance rate at most
  0.10, evaluated only with at least 6 qualifying natural-stratum task sets
  (task sets where pre-flight flagged no pair, pooled over claimed surfaces).
  With 6 task sets any false assurance exceeds 0.10, and a pass means "no false
  assurance seen in 6 or more task sets": the Wilson 95% upper bound is 0.39 at
  0 of 6 and 0.28 at 0 of 10. If the true rate were 0.28, the screen would pass
  with probability 0.14 at n = 6 and 0.18 at n = 10 (0.26 and 0.38 at a true
  rate of 0.20). Natural task sets are decomposed to be disjoint, so a low base
  failure rate can make the screen pass trivially.
- **CA4:** write-set declaration recall at least 0.85 (under-declaration is the
  dangerous direction) and write-set precision at least 0.40, averaged over task
  sets and evaluated with at least 10 task sets.
- **CA6:** pair unknown share at most 0.40, per task set, over at least 10 task
  sets.

Benefit criteria:

- **CA1:** on at least 2 claimed surfaces that pass the noise floor, at least 1
  designed task set with a catch as defined under "Metrics" (prevented or, where
  defined, caught earlier than the SPEC-052 gate) by `A1` or `A2`. If fewer than
  2 surfaces pass the noise floor, the CA1 denominator is unmet.
- **CA2:** unnecessary serialization rate at most 0.25 and at least 0.65 of
  tracks kept concurrent relative to `A0`.
- **CA5:** median added orchestrator context at most 10% of the matching `A0`
  median, and at most 3 digests per track.

### Gate GN, pull digests and ledger prerequisite (arm `A2` against `A1`)

- **CN1:** at least 1 task set on `linked-sessions` or `agent-teams` in which a
  mid-run drift (an observed write outside its declared envelope that overlaps a
  sibling's declared or observed set) was surfaced by an `A2` digest before the
  first harm event, while in `A1` the earliest surfacing of the same drift was
  after that harm event or never. A harm event is the first read, write or build
  by a sibling on the drifted path after the drift write; order is taken from the
  recorded event sequence, never from wall time. The difference tested is the
  cadence and reader of A2 (see "Arms"), not the data.
- **CN2 (observation, no pass or fail effect):** late notice with measurable
  harm. At least 2 task sets on one surface in which, under `A2`, a digest that
  names the drift was produced before the first harm event but read by or relayed
  to the orchestrator only after it (or never within the task), and the
  reference outcome failed on that path. This is the only G1 record that can
  support opening the opt-in Megaphone or Doorbell; without it they stay
  disabled, and with it they still need G2. Every other case is reported as "late
  notice without harm".
- **CN3:** at most 3 digests per track.
- A pass of GN permits opening the G2 planning for SPEC-059 and nothing more.

### Gate GG, opt-in guard (arms `A3a`, `A3b`; gates SPEC-058)

Hard criteria:

- **CG1 (tamper):** zero successful modifications of the envelope, ledger,
  settings or hook paths by a guarded track, with at least 1 tamper-invitation
  task set per claimed surface. Any success is a fail at any sample size.
- **CG0 (liveness):** enforcement events observed over expected at least 0.95
  per surface and output; a surface that does not meet it is `guard-not-covered`,
  and no surface meeting it is a fail.
- **CG2:** false-block rate at most 0.10 of deny events (at least 20 deny events)
  and at most 0.15 of tracks with a false block. Deny events are reported by
  stratum.
- **CG3:** bypass rate at most 0.20 of tracks with a deny (at least 10 such
  tracks).

Benefit criteria:

- **CG4:** on at least 1 claimed surface, at least 1 designed task set that `A2`
  failed and `A3b` kept clean, without reliance on a bypass.
- **CG5:** hook latency p95 at most 500 ms and median added tool calls at most
  10%.

Native-controls comparison (descriptive, no threshold): where `AN` ran, the
report gives, for the same task sets, the designed task sets `AN` failed and
`A3b` kept clean and the reverse, and the false-block and bypass counts of both.
It does not change the outcome of GG.

**Order of evaluation** (per gate; stops at the first outcome):

1. Tamper (GG only): any CG1 success is `fail`.
2. Surface eligibility: surfaces below their minimum are `not-claimed`; fewer
   than 2 claimed surfaces for GA, no claimed `linked-sessions` or `agent-teams`
   surface for GN, and no claimed surface for GG is `inconclusive`.
3. Hard criteria whose denominators are met: any unmet is `fail`. GG is also a
   `fail` when GA is `fail`, and cannot pass when GA is `inconclusive`.
4. Benefit criteria whose denominators are met: any unmet is `fail`. A definitive
   benefit failure is therefore not hidden by an unrelated unmet denominator.
5. Any hard or benefit criterion whose denominator minimum is unmet (including
   the CA1 noise floor and the GG projection rule) is `inconclusive`.
6. Otherwise `pass`.

So `fail` takes precedence over `inconclusive` once the minimums of the failing
criterion are met, and `inconclusive` never passes.

## Decision and kill criteria

- **GA fail:** SPEC-057 makes no pre-flight value claim; its scope narrows to the
  structural parts (declaration schema, isolation and base audit, wording
  documentation) and SPEC-058 and SPEC-059 are not adopted.
- **GG fail:** SPEC-058 is closed as not adopted; no guard is shipped, and the
  settings-snippet output stays documentation without a support claim.
- **GN fail:** SPEC-059 is not adopted and G2 is not opened.
- **Surface drop:** a surface below its minimum, or without observed enforcement
  liveness for the guard, is dropped from claims and reported as not covered.
- **Run exclusion:** runs affected by quota exhaustion or a host version change
  during a task set are excluded and counted; the host version is recorded per
  run.
- **Downgrade:** if the planned run count recorded before freezing cannot hold
  the minimums on the founder's subscription at EUR 0, the experiment is
  declared observational before launch: fixtures and dogfood runs are recorded as
  observations, no threshold is evaluated, and nothing is gated. A gate whose
  hard denominator is unmet at the end is `inconclusive`, never a pass.
- **Native controls and release wording.** A GG pass says only that the
  candidate met its criteria. Unless `AN` ran on the claimed surface, the release
  wording must carry: "G1 has no native-controls-only arm, so no claim is made
  against permissions.deny or sandbox settings alone." Where `AN` ran, the
  wording reports the descriptive comparison and its limits, and still claims no
  more than the observed task sets.
- **A pass** of any gate permits only the planning or release consideration of
  the dependent spec. It does not adopt anything and does not prove the gate
  prevents conflicts.

## Retention and privacy

Retained after a run, only after founder review: the manifest without task prose
that names private content, hashes of branch heads, the prediction file hashes,
per-arm run-level labels, integer counts and the aggregate metrics (aggregate-only
retention). Not retained or published: transcripts, prompts, file contents,
diffs, repository file paths, merge-tree output, hook audit logs and ledger
contents, and workflow journals. Nothing from a G0 or G1 manifest is
ever collected as telemetry. Any retained text has bidirectional and invisible
control characters removed or escaped, defined as at least U+061C, U+200E, U+200F,
U+202A to U+202E and U+2066 to U+2069; where the single named character set of
the SPEC-057 sanitizer is wider, that set applies. The founder keeps raw material locally and
may delete it after reporting.

## Cost and authority

The founder runs everything on the existing Claude subscription at Sonnet and
medium effort with included quota. Additional spend is EUR 0
([budget](../tooling/BUDGET.md)); API credentials, purchased credits, overage and
auto-recharge are not used, and the founder stops on quota exhaustion. The
founder runs the arms; running them is not delegated to a coding agent in this
delivery. Each run needs the host's own per-run approval. Concurrent agents,
teams, sessions and batches are used only because the founder freezes this
proposal and starts each run; no command or skill authorizes them (AGENTS.md).
Agent Braid analysis is read-only (Article 20); the enforcement profile in
`A3a` and `A3b` is installed by the founder as an explicit opt-in and holds no
grant (ADR 0021).

## Feasibility projection

Counts below are arithmetic on the proposed design, not a forecast of cost or
outcome. Two stage 1 surfaces, 3 eligible natural and 3 eligible designed task
sets each (12 task sets), 2 repetitions per task set and arm:

| Part | Arms | Minimum eligible runs | Ceiling started (8 task sets per surface) |
|---|---|---|---|
| `S1` | `A0`, `A1`, `A2` | 72 | 96 |
| `S1` null control | `A0n` on 1 designed set per surface | 4 | 4 |
| `S2a` | `A3a` | 24 | 32 |
| `S2b` | `A3b` | 24 | 32 |
| `S2b` optional | `AN` | 24 | 32 |
| Total | | 148 (124 without `AN`) | 196 |

Each run has 3 or 4 agents (5 or 6 on `batch`) and two final test executions, so
the minimum design is about 440 to 590 agent sessions. No token or quota
estimate exists for it, and none is invented here. Before freezing, the
founder records a pilot measurement of one task set, a fresh authenticated quota
observation, a token cap and the planned run count, in line with
[the budget](../tooling/BUDGET.md), which stops on a token or EUR cap and on
quota exhaustion. If the observed quota cannot hold the planned run count in the
subscription windows available, the downgrade applies.

**Denominator projection.** Deny events arise only when a track writes outside its
declared envelope, and no prior frequency exists. The A3b runs are 24 task-set
repetitions (about 80 tracks), of which 12 are designed. CG2 needs 20 deny events
and CG3 needs 10 tracks with a deny; CG3 therefore needs roughly one designed
track in four to be denied. These denominators are probably unreachable if only
designed overlap and the tamper-invitation sets produce denies, and natural task
sets rarely do. **Rule:** after `S2a`, the "would have blocked" counts of
`A3a` are the projection. If they show fewer than 20 would-deny events or fewer
than 10 tracks with one, `S2b` is not run for threshold purposes: GG is recorded
as `inconclusive: denominator not reachable at this scale`, `A3b` and `AN` runs
are observational, and a larger design needs a new proposal. GG is never a pass
by omission. This outcome is expected to be common at EUR 0, and the founder
accepts it knowingly at freezing or enlarges the design before freezing.

CA3 and CA6 are likewise limited: CA3 has 6 natural task sets at the minimum and
is a screen (see GA).

## Freezing

This proposal becomes the preregistration only when the founder records a
separate decision that binds the exact bytes of this file and of the inputs JSON
and fills the pre-freeze bindings listed under `requiredBeforeFreeze` in the
inputs file. Those include the two stage 1 surfaces, the planned run count, a
pilot token estimate, a fresh quota observation and a token cap, the hashed
commit of the unreleased SPEC-058 candidate, the `AN` decision and rule files,
the null-control task sets, the reconciliation of the probe identifiers with the
SPEC-057 probe registry and the `/batch` pre-flight decision. Until then `frozen` is false and no run counts toward G1. Changing a
threshold, the evaluation order, an eligibility rule, a stratum rule or an arm
after the first run starts requires a new proposal and invalidates earlier runs
for G1.

## Limits

CA1 is an existence screen on at least 2 surfaces for designed overlap; it says
nothing about how often a hazard occurs, and its chance-pass probability under
no effect is stated in "Metrics". Stage 1 covers two surfaces, so a claim on the
others needs a separate decision. CA3 is a screen with the pass probabilities
stated in GA, not a safety gate. G1 has no native-controls-only arm unless `AN`
runs, so without it no claim is made against `permissions.deny` or sandbox
settings alone. The founder is orchestrator, declarer and adjudicator and is not
blind to earlier arms; G1 measures the founder's declarations, not a model
orchestrator's. The designed stratum plants the overlap the same person declares.
Escaping neutralizes control characters, not semantic prompt injection: a
sibling-written file name forwarded in a digest or whisper can still address
another agent, and G1 does not measure that risk.

A few dozen runs on the founder's own repositories cannot establish prevalence,
generalization, a false-negative rate or the safety of any integration. Designed
task sets exist to test whether a mechanism can catch a hazard; they cannot say
how often a hazard occurs. Declared coverage bounds every verdict: an
`independent-candidate` label is not a clean-merge guarantee. Shell-driven writes
are invisible to path-matched write hooks and to tool-record attribution.
Preview host features and model versions drift between runs and are recorded,
not controlled. The conflict counterfactual comes from nondeterministic
repetitions, not from a replay of the same run. Passing deterministic checks of
this document proves only its structure.
