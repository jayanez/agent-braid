# SPEC-065: Implementation plan

## Technical context and scope

Python 3.12+ standard library only, macOS (founder's machine), Claude Code CLI
2.1.292 observed. Four deliverables (spec REQ-001 to REQ-010): the native manifest
profile, the macOS containment backend with contained launcher, the native
`ClaudeTransport`, and the qualification probe runner plus human issuance
procedure. Planning only: no code, ADR or shared tracking file changes in this
feature's specification PR.

Planned target files (implementation tasks, after founder decisions):

| File | Change |
|---|---|
| `agent_braid/harness_manifest.py` | add the native profile beside the offline one |
| `agent_braid/harness_containment_macos.py` (new) | `ContainmentBackend` subclass, policy builder, contained launcher, F4 pre-session check (NC-11), run evidence |
| `agent_braid/harness_transport_claude.py` (new) | native `ClaudeTransport` using the contained launcher and quota gate |
| `agent_braid/harness_quota.py` (new) | typed quota reading, freshness and D2 cap gate (input only, no network) |
| `agent_braid/harness_qualification_probes.py` (new) | versioned probe catalog and runner; writes evidence, never records |
| `tests/test_harness_manifest.py` | offline byte-compatibility goldens, native schema negatives |
| `tests/test_harness_containment_macos.py` (new) | policy, refusal and self-check tests; live probes skipped unless explicitly enabled |
| `tests/test_harness_transport_claude.py` (new) | transport refusal matrix with a fake launcher |
| `tests/test_harness_quota.py` (new) | freshness and stop conditions |
| `tests/test_harness_qualification_probes.py` (new) | catalog shape, pass rule, no-record-writing |
| `specs/065-native-claude-containment/evidence/**` | decision records, probe bundles, hand-off packet |

The verifiers and record formats are reused unchanged. The following changes
to existing modules are already known (analysis A2, A3, A8); each is a separate
reviewed edit with its own negative tests, and any further change found
unavoidable is handled the same way:

| Id | File | Change | Why |
|---|---|---|---|
| K1 | `harness_host_claude.py` or the T006 launcher | live `init` parsing; kill the group when `apiKeySource` is outside the subscription set, before any `assistant`/`result` event is accepted | `run_claude` parses stdout only after `transport.run` returns, so a paid route would otherwise run to completion (F2) |
| K2 | `harness_host_claude.py` | native transport refuses unless its backend passes the verified-containment check of `_check_backend` (same environment hash) | `_check_transport` never inspects a backend; a host qualification alone would pass |
| K3 | `harness_host_claude.py` | native-only session wall bound ≤ F3 30 min (value NC-8) | `HostLimits` is capped by the shared `MAX_WALL_SECONDS = 60`; the shared constant and Codex stay unchanged |
| K4 | `harness_host_claude.py` | `ENV_ALLOW` for the native launcher gains the variables NC-5/NC-7 require (`CLAUDE_CONFIG_DIR`, `TMPDIR`; NC-5 chose the dedicated user's own login, so no token variable); `argv[0]` becomes the absolute pinned executable path, hash-checked at every launch | today `ENV_ALLOW = ("HOME", "PATH")` and `argv[0]` is a bare `claude` resolved through `PATH` |
| K5 | `harness_host_claude.py` | only if CRED-05 observes it: `SUBSCRIPTION_KEY_SOURCES` change backed by the probe record | the set is a fixture assumption |

Quota readings and the qualification hash are recorded in a run-evidence record
written by the native transport and backend, so `ClaudeHostResult`, `LabResult`
and the `ClaudeTransport.run` signature stay unchanged.
`agent_braid/harness_hosts.py` is SPEC-048/T008's target and is not created here.

## Constitution check before research

| Article | Obligation | Plan response |
|---|---|---|
| 0, 13, 17 | no inflated claims; class is not evidence | records are evidence about one machine; no confluence or Yang–Baxter claim |
| 4 | verified, never presumed | qualification requires probes per effect; pairwise or partial passes do not imply profile qualification |
| 5 | hidden effects are uncertainty | four effects declared; unobserved CLI effects (R7) are probe inputs; `inconclusive` blocks |
| 6 | execution contract preserves semantics | native runs only under a verified contract; refuse on any mismatch |
| 7 | isolated execution is a distinct stage | backend and transport are separate modules from admission and observation |
| 12 | isolation is a systems mechanism | OS-level enforcement; prompts and tool allow-lists are not counted as containment |
| 14 | evidence, not verdicts | bundle with commands, exits, hashes and limits; records cite the bundle hash |
| 15 | declared metadata not blindly trusted | expected hashes supplied out of band; manifest hashes re-verified |
| 19 | real problem | unblocks the native measurement SPEC-049 needs |
| 20 | analysis separate from execution | no change to analyzer contracts; `executionAuthorization` stays false |
| 24 | semantics before production | contracts are proposals until reviewed |

No MUST conflict found. SHOULD deviation: none. ADR 0019 defers arbitrary
commands until enforceable OS isolation exists; this feature runs one fixed
executable under a qualified policy and does not lift that deferral for
general commands (see proposed ADR below).

## Research, assumptions and alternatives

See [research.md](research.md). Not an empirical comparison: no sampling frame,
labels or held-out units. The probe catalog is a fixed engineering test set; its
yield is "every probe ran with a passing positive control", and a shortfall is a
feasibility result.

Assumptions: the founder's machine is single-operator; the CLI binary at the
pinned hash is the vendor's; same-UID processes outside the sandbox are not
hostile during a run (residual risk recorded).

## Design and compatibility

1. **Profile dispatch.** `parse_manifest` reads `profile` first and calls the
   existing offline validator unchanged or a new native validator. Offline
   constants and the `PROFILE` name keep their values; goldens prove identical
   bytes, digests and refusals (SC-001).
2. **Backend.** One policy object built from the founder decisions renders the
   isolation profile (NC-2) and the launch environment: no inherited
   environment, `HOME`/`CLAUDE_CONFIG_DIR`/`TMPDIR` locations per NC-5 and NC-7,
   allow-listed executables per NC-8, network rule per NC-1. Both entry points
   (`run` for fixtures, `launch` for the CLI) use the same policy object and
   report `kind = "native"` with the same qualification. Unavailable mechanism,
   compile failure, self-check failure or unsupported version raises a
   fixed-reason refusal before any child starts.
3. **Transport.** `version()` runs the pinned executable with `--version`
   inside the same containment; `run()` calls the quota gate, the F4 check
   (NC-11), then the contained launcher with the `LaunchPlan` argv (K4),
   watching `init` live (K1), and returns `HostRun`. `run_claude` keeps all
   stream, route and drift checks. No retry, no alternative route.
4. **Quota gate.** Pure function over a timestamped reading (source NC-6), the
   F3 caps and caller-supplied cohort state (units used, cohort weekly use;
   owned by SPEC-049); returns proceed or a fixed stop reason, and refuses when
   cohort state is absent. Post-reading is stored in the run evidence.
5. **Probe runner.** Runs the catalog in uncontained-control and contained
   modes, writes the bundle, computes per-effect status. It has no function
   that writes a qualification record; a test asserts that.
6. **Issuance.** A founder decision record in
   `specs/065-native-claude-containment/evidence/qualification/` contains both
   records' canonical bytes and hashes, the bundle hash and the issuer
   statement. The trusted hashes are passed to the runtime from that record.

Compatibility: as in spec.md. No change to plugin, AIM, grants, telemetry,
observation format or qualification formats.

## Validation strategy

Requirement → scenario → procedure → evidence is in
[validation-plan.md](validation-plan.md) and [assurance.json](assurance.json).
Negative controls: every refusal reason in REQ-001 to REQ-009 has a test; every
escape probe has a positive control (REQ-010). Deterministic unit tests do not
count as qualification evidence; only the bundle and the human records do.
Validation profiles: `quick` after each increment, `pr` on the stable candidate,
both in a clean clone while the shared object store fails the portable-root
check.

## Constitution check after design

Unchanged: no MUST conflict. The design keeps execution authority false, keeps
issuance human, refuses rather than degrades, and labels every result with its
backend and qualification. Residual risks (deprecated mechanism, same-UID
interference, kernel bugs) are stated, not hidden.

## Proposed shared-file changes

Not made by this feature; listed for the orchestrator and founder:

- `docs/adr/` — new ADR "Native Claude laboratory containment" (proposed
  number: next free) recording the NC-2 mechanism, the STRICT policy, the
  human-issuance rule and the explicit non-lifting of ADR 0019 for arbitrary
  commands; amends the ADR 0027 boundary for the Claude profile only once
  accepted.
- `docs/development/SPEC_MILESTONE_INDEX.md` — add SPEC-065 under the HAR track
  (HAR.1, as the prerequisite of SPEC-048/T008 Claude).
- `docs/development/github-tracking.json` — made in this PR with orchestrator
  approval, because every `specs/` directory needs a mapping for validation to
  pass: `specs["065-native-claude-containment"]` in "HAR.1 — Braid Harness
  laboratory", state `open`. Still proposed: `project_review_pending` += `SPEC-065`.
- `ROADMAP.md`, `docs/STATUS.md` — one line each: SPEC-065 specified; founder
  decisions NC-1 to NC-11 recorded (T001); next T002 ADR.
- `specs/048-harness-variant-laboratory/tasks.md` T008 — add dependency on
  SPEC-065 T010 for the Claude profile (by the T008 owner).
- `specs/049-harness-evaluation-learning/tasks.md` T004 — dependency chain note
  via SPEC-048/T008 (by the T004 owner).
- `scripts/validate_change.py` — classify the new `harness_*` modules and tests
  under the existing harness rule, if not already covered by its globs.

## Human review and unresolved decisions

Decided: NC-1 to NC-11 and the F5 binding, in
[evidence/founder-decisions-20261031.json](evidence/founder-decisions-20261031.json)
(T001). Pending: human review of this specification; ADR acceptance (T002)
before any native session.
