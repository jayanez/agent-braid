# T001 kickoff decision: offline foundations

Status: **proposed; founder architecture/security decision pending**.
Prepared on 2026-10-21 against Agent Braid
`a6329c828011d1468fed3dfa4e98f5a8531167e2`. This supplements the
[ADR proposal](adr-proposal.md), [interface](contracts/interface.md) and
[T001](tasks.md); it does not adopt them, complete T001 or activate a laboratory.
Trace: 048/REQ-001/SC-001, REQ-003/SC-003, REQ-004/SC-004,
REQ-007/SC-007. The owner authorized parallel preparation of dependency-independent
tracks. That instruction is not recorded here as architectural adoption.

## Proposed decision and first implementation boundary

Adopt an internal, standard-library, **offline-only** first slice for T002–T004:
immutable manifest verification, bounded candidate import and externally issued
laboratory-admission validation/reservations. Include no launcher, model-callable
issuer, native route, automatic retry, promotion or host/global configuration change.
Keep the initial editable surface to positively inventoried task-local guidance
and a selection/order of already authorized context entries. Every consumer checks
the exact candidate/base/source/policy/tool/verifier/context binding independently.
Unknown provider identities remain explicit; they cannot qualify a native profile.

This slice is more useful than manifest-only work because it tests the file and
authority boundary. Starting with the runner would pull in T011/T012 and recovery
before their foundations exist. Native-first work has no qualified effect profile.

| Permitted laboratory effect | Limit and verification obligation |
|---|---|
| Read manifest, candidate, base and context-inventory bytes | Positive source inventory; strict type/encoding/size checks; full hashes. Reject traversal, symlinks at any admitted path component, special files and external resolved paths before import. Do not discover unrelated roots or credentials. |
| Materialize accepted guidance/context selection | Only in a new operator-owned private destination outside the source tree. Validate the complete candidate before materialization; partial failures remain inspectable and cannot become an accepted candidate. |
| Write admission/reservation and bounded diagnostic records | Exact manifest/envelope identity, single-use reservation, external issuer and expiry. No existing runtime grant is reinterpreted. A record or digest alone supplies no permission. |
| Delete failed staging artifacts | Only the exact owned staging inventory; retain failure/cleanup receipts. Source deletion and ref promotion are excluded. |

Candidate text is untrusted data even when it resembles instructions or claims
approval. Immutable layers include `CONSTITUTION.md`, `GOVERNANCE.md`, AGENTS and
host instructions, `.specify/**`, generated skills, acceptance verifiers/graders,
permissions/issuers, tools/scripts/hooks/plugins, model/provider settings, source
baselines and output destinations. A matching filename or textual prefix cannot
override the positive inventory or protected-layer precedence. Grader bytes are
excluded from candidate context even when their hashes are needed for identity.

The operator, OS and installed trusted implementation are trusted. Candidate data
and imported observations are adversarial inputs. Hostile same-UID ancestor-path
replacement, a compromised kernel/operator and power-loss durability are outside
this proposed first profile. Descriptor/path checks still need adversarial tests;
excluding hostile same-UID interference does not excuse ordinary symlink or stale
input checks. A worktree, prompt or manifest is not an arbitrary-code sandbox.

## Numerical envelope proposed for adoption

All limits below are **proposed**, with no obtained HAR implementation evidence.
They govern laboratory attempts, not this developer chat or operator-run repository
validation. A later implementation must reject unsupported bounds instead of
advertising a stronger guarantee than it can enforce.

| T002–T004 foundation limit | Proposed enforcement and present feasibility |
|---|---|
| Native/model sessions, child processes, network connections: **0**; additional cash: **EUR 0** | Exclude launch/provider/network paths entirely. No paid fallback. No native route or economic acceptance is inferred from the existing subscription. |
| Manifest record: **1 MiB**; JSON nesting: **16** | Bounded byte read before parsing, strict duplicate/unknown-field/type checks, finite numbers and canonical SHA-256 identity. Software bounds are implementable; HAR checks are not implemented yet. |
| Candidate: **32 files**, **32 KiB/file**, **256 KiB total**, relative path depth **4** | Bound enumeration and reads, including rejected entries, before allocation/materialization. Never follow a supplied symlink or silently truncate to make an import pass. |
| Context: **16 entries**, **128 KiB total** | Record the selected inventory and omissions; enforce packaging in T011. Byte limits do not assert a provider token count. |
| Diagnostics/output: **64 KiB/stage**; journal/export allowance: **8 MiB/run** | Reserve bytes before writes. Explicit loss receipts distinguish bounded presentation from complete private evidence. T012 owns privacy/export enforcement. |
| Admission: **300 seconds maximum**, one exact manifest/envelope, one reservation | Trusted clock/issuer; reject stale or replayed admission. Recovery never renews it. T004 validates/reserves; it has no dispatch path. |

Future T005 fixture targets are separate: **one round, width 1, four probes**
(base/general/task-specific/composition), at most **three proposal/composition
stages, one selection and one reflection**, and **zero automatic retries**.
All nine possible stage entries count; cached or interrupted work remains visible.

| Prospective fixture target | Qualification still required before T005 dispatch |
|---|---|
| **10 seconds/probe**, **120 seconds/experiment**, including **10 seconds reserved for cleanup** | Shared monotonic deadline; stage budgets only tighten it. Observe termination and cleanup before reuse. Cooperative checks do not establish a hard wall-time bound for blocking filesystem I/O. |
| **One supervisor plus one allowlisted fixture child**, no grandchildren | Fixed owned fixture entry points, no candidate-supplied command/argv. Test child settlement and deliberate interruption. This is not OS containment for untrusted native hosts. |
| **10 CPU seconds/child**, **256 MiB RSS threshold**, **64 MiB total scratch** | CPU enforcement and accounting require platform checks. RSS is a proposed monitored stop threshold, not an observed hard memory limit. Scratch reservations and observed usage must include cleanup; no filesystem-quota guarantee is currently established. |

If a claimed profile needs a hard bound or denial that the host cannot enforce,
that profile remains unavailable. Fixture observations must disclose overshoot,
missing measurements and cleanup uncertainty. They cannot qualify native hosts.

## Host feasibility observed, without host execution

Read-only inventory on 2026-10-21 found Darwin arm64, macOS `27.0.1`, a Codex
executable in the ChatGPT application bundle, a Claude symlink resolving into
`claude-code/2.1.292`, and an installed Python 3.13 path. The directory names are
not authenticated host/build observations. No host was invoked; route, quota,
subscription fallback, credentials, filesystem/network denial, descendants,
streaming, cancellation and independent outcome support remain **unqualified**.
Codex and Claude therefore both have native status **unavailable**, independently.

## Compatible seams at the inspected baseline

| Owning source | Reuse decision and boundary |
|---|---|
| [`system_one.py:37–158`](https://github.com/jayanez/agent-braid/blob/a6329c828011d1468fed3dfa4e98f5a8531167e2/agent_braid/system_one.py#L37) | Assess immutable JSON, canonical bytes and strict parser reuse against HAR record/byte limits; do not invent competing digest semantics or import synthetic decision-domain acceptance. |
| [`analysis.py:160`](https://github.com/jayanez/agent-braid/blob/a6329c828011d1468fed3dfa4e98f5a8531167e2/agent_braid/analysis.py#L160) | Reuse conservative effect/dependency classifications. `independent-candidate` still requires an execution contract before parallelism. |
| [`tooling_sessions.py:109`](https://github.com/jayanez/agent-braid/blob/a6329c828011d1468fed3dfa4e98f5a8531167e2/agent_braid/tooling_sessions.py#L109) | Adapt durable-start/single-dispatch and exact reconciliation semantics for T007; do not use M4.5 admission DTOs as HAR authority. |
| [`system_one_verified_selection.py:112`](https://github.com/jayanez/agent-braid/blob/a6329c828011d1468fed3dfa4e98f5a8531167e2/agent_braid/system_one_verified_selection.py#L112) | Reuse shared-budget/deadline and cleanup-reservation patterns after contract review. Its finite patch domain and cooperative timing remain bounded. |
| [`system_one_verified_registry.py:71`](https://github.com/jayanez/agent-braid/blob/a6329c828011d1468fed3dfa4e98f5a8531167e2/agent_braid/system_one_verified_registry.py#L71) | Preserve independent verifier pins; its literal-patch verifier is not a general harness grader. |
| [ADRs 0019/0020](../../docs/adr/0019-bounded-local-git-runtime.md), [`runtime_policy.py:215`](https://github.com/jayanez/agent-braid/blob/a6329c828011d1468fed3dfa4e98f5a8531167e2/agent_braid/runtime_policy.py#L215) | Reuse owned-state techniques, not grant authority. The accepted fixed-patch operation language still excludes arbitrary commands and native host launch. |

No FC.1/FC.2, M4/M4.5, telemetry, System One or plugin gate transfers to HAR.
Existing analysis-only consumers continue to return `executionAuthorization=false`.

## Selected upstream inventory actually inspected

The existing local audit checkout is at
`google-research/harness2@1cfe254e8d25b15f37048c3730134686abe60335`.
Committed bytes and local file bytes matched for all rows below; SHA-256 values
also match [source-identity.json](research-evidence/source-identity.json).
Inspection covered each selected code header and the named mechanisms, not an
exhaustive security review. No upstream code was imported in this preparation.

| File; selected portion and target | Exact file SHA-256 |
|---|---|
| `harness2/core/spec.py`; `ChannelSpec`, `RunView`, `BenchmarkAdapter` → T002 typed seams | `f245ec9e314778e2a1a51594b906584255b9eed8340c073b864a8a6f2c8dc400` |
| `harness2/substrate/base.py`; `Install`, `RunRequest`, `Substrate` → typed manifest/host boundary; launch methods deferred | `50a63f174e3772888af3882f3ffff3162cefba8d36e927b1a5de343c5806dd16` |
| `harness2/core/runmark.py`; `fingerprint`, completion markers → T002/T007; replace shortened SHA-1/base sentinel with full manifest identity | `99a7c3f0b023623224c3376bc0390e985b8e6608f0928d34b821ffe6c36f9175` |
| `harness2/core/tree.py`; `SurfaceSpec`, `normalize_rel`, `read_tree`, `validate` → T003; replace permissive path/read/encoding behavior with HAR checks | `c2a15690b1b6b02156e922c5e0b1a215c5065d7bea5a3bae2e56b47309197552` |
| `harness2/core/ledger.py`; `Entry`, `Ledger`, stage identities → T004; add reservations, unknown costs and selection/reflection accounting | `7059de5d90fc9fb8d4b3b799ff075f09d34f182ba0fdb56eb9d8b8383d0bbf55` |
| `LICENSE`; Apache License 2.0 text, section 4 inspected | `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30` |

All five selected code headers identify **Copyright 2026 Google LLC** and
**Apache-2.0**. The pinned root tree has no `NOTICE` file. Before incorporating
derived portions, retain applicable upstream copyright/license/attribution
notices, distribute the Apache license text, and add prominent changed-file
notices describing Agent Braid's modifications. Preserve terms on source portions;
do not silently relabel them under the repository default. Final license-text,
`NOTICE` and `docs/development/THIRD_PARTY.md` additions need integration impact
review under the existing [license map](../../LICENSE). Those destinations and
the exact adapted line ranges remain proposed until a concrete port exists.
Excluded assets, benchmark runners and dependencies receive no license clearance
from this inventory. Upstream branding and bypass launch flags remain excluded.

## Decisions, verification and stop conditions

The recommended founder decision is to adopt only the offline architecture and
foundation envelope above, with T005 targets still prospective. Adoption must name
the exact reviewed candidate/document identity, scope, actor and decision; use the
next available canonical ADR number only after authority-inventory impact review.
Do not reserve 0026 or rebind historical planning approvals. Until that decision
exists, T001 stays pending and executable T002–T004 work does not begin.

After adoption, implement T002, then T003; T004 follows T001/T002 and may proceed
independently of T003 only with explicit file ownership. Require positive and
negative tests for changed identities, malformed/non-finite records, path/symlink
escapes, protected mutations, injection, missing/stale/replayed authority and
exhausted reservations. Run the relevant quick profile after coherent edits and
the PR profile on the stable candidate. Frozen candidate/input/output evidence,
independent Luna review when authorized, human adoption and hosted CI are separate.
This document claims no executed HAR acceptance tests or native/economic result.

T011/T012 must precede the T005 fixture runner. T007 then establishes durable
interruption/reconciliation controls before recovery/integration acceptance.
`T009` deterministic integration does not
wait for native T008. Before any native dispatch, complete the host-specific
T013/T014 implementation and independent T008 qualification, then fresh exact
source/route/quota/operator admission; `049/T004` separately gates a native cohort.
Human promotion and future automatic-policy adoption remain distinct decisions.

Stop on identity/protected-layer drift, authority mismatch, reservation exhaustion,
missing terminal observations or unsettled cleanup. Preserve the immutable base,
failed attempt and unknown costs; do not retry, infer completion, renew authority
or promote an output. Report continuity and coordination separately from the first
fixture cohort; a combined score cannot conceal either axis's regression.
