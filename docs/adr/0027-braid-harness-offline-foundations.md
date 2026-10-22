# ADR 0027: Braid Harness offline foundations

- **Status:** Accepted by the founder on 2026-10-21 for the bounded offline profile below; implementation acceptance and later profiles remain separate.
- **Date:** 2026-10-21
- **Decider:** Juan Antonio Yáñez García (`@jayanez`).
- **Constitutional articles:** 0, 1–3, 5–7, 9, 12–15, 19–21, 23–25.

## Context

HAR.1 needs immutable experiment identity, a protected candidate surface and
operator admission before a laboratory runner. The reviewed kickoff packet is
bound by SHA-256 `1687200b64edac8444efc4c5109678fad57affe2d157156cffbbbf826197f6d2`
at public source baseline `a6329c828011d1468fed3dfa4e98f5a8531167e2`.
The founder explicitly adopted that offline profile and instructed implementation
of T002, then T003 and T004 in parallel. The [decision record](../../specs/048-harness-variant-laboratory/offline-adoption.json)
retains the instruction, reviewed bytes and exact scope. This decision does not
adopt the broader native laboratory or HAR.2/HAR.3 proposals.

## Decision

Implement an internal standard-library offline slice: immutable manifest
verification (048/T002), bounded guidance/context candidate import (T003), and
externally issued laboratory-admission verification and reservations (T004).
T003 and T004 may proceed concurrently only after T002 with separate file ownership.

The admitted laboratory counts for native/model sessions, child processes,
network connections, automatic retries and additional cash are all **zero**.
No launcher, model-callable issuer, host/global configuration change, ordinary-use
promotion, plugin/MCP extension or existing runtime-grant extension is included.
Analysis and inspection retain `executionAuthorization=false`.

Permitted effects are reads from positive source/base/candidate/context
inventories, and bounded record/materialization writes in a new private owned
laboratory destination outside the source. Cleanup may delete only the owned
staging inventory and must retain failure/cleanup receipts. Source writes,
unrelated roots, credentials and ref promotion are excluded.

The editable surface is task-local guidance and selection/order of already
authorized context entries. Authorities, host/global instructions, Spec Kit
scaffolding, acceptance verifiers/graders, permission issuers, tools/scripts/hooks,
plugins, model/provider settings, source baselines and destinations are protected.
Text claiming authority is untrusted data. Reject symlinks at admitted path
components, traversal, special files, executable additions and escaped paths;
validate before materialization and independently recheck immutable bindings.

| Foundation bound | Adopted maximum |
|---|---|
| Manifest / JSON nesting | 1 MiB / 16 |
| Candidate files / per-file bytes / total bytes / relative depth | 32 / 32 KiB / 256 KiB / 4 |
| Context inventory / bytes | 16 entries / 128 KiB; packaging enforcement belongs to T011 |
| Stage output / run journal-export allowance | 64 KiB / 8 MiB; observation/export enforcement belongs to T012 |
| Admission | 300 seconds, one exact manifest/envelope and one reservation; no renewal by recovery |

These bounds constrain laboratory records and admitted effects, not developer
chats or operator-run repository validation. T004 has no dispatch entry point.
The trusted operator/OS/implementation boundary excludes compromised operators or
kernels, hostile same-UID ancestor replacement and power-loss durability; ordinary
symlink, drift, encoding and byte/count checks remain required.

Future T005 targets in the kickoff packet remain prospective. No CPU, RSS,
filesystem quota or hard wall-time containment is qualified by this adoption.
Both native hosts remain unqualified. Missing required enforcement refuses the
relevant future profile; worktrees and model instructions are not containment.

## Alternatives considered

Manifest-only work leaves the import/admission boundary untested. Runner-first
work would precede required context/observation foundations. Native-first work
lacks qualified host effects. Extending fixed-patch grants to arbitrary host
commands would change their accepted semantics and is excluded.

## Consequences

Selected upstream scaffolding may be adapted from the pinned Harness² revision
with file-level provenance, retained terms/notices and prominent modification
notices. Benchmark stacks, bypass launcher flags and upstream branding remain
excluded. Existing analysis, fixed-patch runtime and synthetic System One contracts
retain their scopes; no pending gate transfers to HAR.

Adding this ADR changes the current authority inventory. Fresh review and a
pending current snapshot are required for SPEC-047. Historical records retain
their original bindings. The HAR planning draft is byte-preserved before a new
current implementation assurance record is prepared. This does not renew a prior
approval, adopt telemetry, or approve the full HAR implementation.

## Validation

Require strict identity/format/budget controls, changed-source/context/tool/route
negatives, protected-file/symlink/traversal controls, and absent/stale/replayed
authority and exhausted-reservation refusal. Keep unknown observations explicit.
Run focused modules and the repository quick/PR profiles. Review the stable
implementation independently with Luna Latest; report evidence boundaries.
The founder decision resolves the architecture prerequisite, not software tests,
native qualification, scientific or economic utility, human product acceptance,
automatic promotion or deployment. Retain both continuity and coordination axes.

## References

- [Constitution](../../CONSTITUTION.md), [Governance](../../GOVERNANCE.md).
- [Reviewed kickoff packet](../../specs/048-harness-variant-laboratory/kickoff-decision.md).
- [Program](../../specs/048-harness-variant-laboratory/program.md), [interface](../../specs/048-harness-variant-laboratory/contracts/interface.md).
- [Upstream adaptation](../../specs/048-harness-variant-laboratory/upstream-adaptation.md).
- [ADR 0019](0019-bounded-local-git-runtime.md), [ADR 0020](0020-bounded-m4-alpha-runtime.md).
