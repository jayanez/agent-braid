# SPEC-081: Pi and ThinkRail host integration

**Milestone:** M4.9 — AI tooling integration for Pi and ThinkRail (new milestone;
owner decision of 2026-11-22 in the [harnessing benchmark](../../docs/strategy/HARNESSING_BENCHMARK.md)).

**Status:** draft, documentation only; nothing implemented, observed, installed or
published. Every Pi and ThinkRail fact below comes from vendor documentation read
once on 2026-11-22 and is unverified until REQ-002 observes it.

## Purpose and scope

Make the Agent Braid plugin installable in Pi (the pi coding agent, repository
`earendil-works/pi`, npm `@earendil-works/pi-coding-agent`) and in JetBrains
ThinkRail (an Apache-2.0 incubator IDE that runs Pi in-process, installs Pi
packages, connects the MCP servers of Pi's `mcp.json` with per-call approval and
imports Claude and Codex skills). This is engineering, not a research protocol. The
precedent is [SPEC-068](../068-opencode-native-integration/spec.md) (OpenCode).
The first phase is observation: no package layout, name or channel is frozen until
REQ-002 records a real install. Whether Pi core reads `mcp.json` is an open
question; a negative observation is a valid result and selects the OD-3 fallback.

In scope:

- a one-command observation capture of Pi and ThinkRail in a disposable profile;
- a Pi package (`package.json` declaring `skills`, and `extensions` only if OD-4
  says so) that carries the seven existing skills plus the SPEC-080 `harness` skill
  when SPEC-080 has merged;
- registration of the unchanged `agent-braid-plugin/v0.2` MCP server in Pi's
  `mcp.json`, only if REQ-002 shows that Pi core reads it;
- a `pi` installer profile, a plugin build target, a read-only diagnosis module and
  the host lists that name supported hosts;
- Pi in the harness host registry as unqualified and offline only.

Exclusions (each is a MUST NOT):

- No native harness sessions for Pi or ThinkRail. Evaluation through Harbor's `pi`
  adapter belongs to SPEC-084.
- No new Agent Braid authority. A Pi package, extension, host approval or ThinkRail
  per-call approval is never an operator grant. `executionAuthorization` stays
  false on every advisory result.
- No change to the bytes Codex, Claude Code or OpenCode read from the shared
  plugin artifact, other than added entries in inventory and provenance.
- No new MCP tool; no change to the `agent-braid-plugin/v0.2` or
  `agent-braid-tooling/v0.2` contracts; no npm publication without OD-1.
- No write to the owner's real Pi, ThinkRail or Gentle AI configuration during
  observation; no secret in the repository, an image or a capture file.

## Requirements and acceptance scenarios

**REQ-001 Owner review.** The owner reviews this spec and plan before any task
after T002 starts.

- **SC-001:** Given this spec, plan and tasks, when the owner reviews them, then
  OD-1 to OD-7 are decided or deferred in a dated record and the authorized tasks
  are named.

**REQ-002 Observation before design.** One command captures, in a disposable
profile, a real Pi install and a ThinkRail install: version and binary hash;
`pi install` from npm, Git and a local path; how skills and extensions in
`package.json` load; whether Pi core reads `mcp.json` (unverified today); the
configuration and session paths; the redacted shape of the session JSONL; and in
ThinkRail the Pi package install, the MCP per-call approval and the skill import.
A dry run sends no prompt.

- **SC-002:** Given the capture script and a disposable profile, when the owner
  runs it, then each matrix row records the observed behaviour, version, command
  and limits, rows not observed stay `unobserved`, raw output stays outside the
  repository and only a redacted summary with hashes is committed.
- **SC-003:** Given a REQ-002 row that contradicts this spec, when the design is
  reviewed, then the affected requirement is amended before T006 starts, and a
  missing Pi core MCP reader selects the OD-3 fallback.

**REQ-003 Pi package with skills.** The plugin build produces a Pi package whose
`package.json` declares the packaged skills (seven, or eight with SPEC-080) with the
same text the other hosts ship, installable by `pi install` through the OD-1 channel.

- **SC-004:** Given a built package, when it is installed in a disposable Pi
  profile, then Pi lists exactly the packaged skills with canonical text, and the
  files read by Codex, Claude Code and OpenCode are byte-identical to the build
  without the Pi target.

**REQ-004 MCP server registration (conditional).** If REQ-002 shows Pi core reads
`mcp.json`, the package or installer registers the `agent-braid` server through the
bundled runtime launcher, requiring an explicit registered `workspaceId` and keeping
the `reconnect-required` semantics. Otherwise the OD-3 fallback applies.

- **SC-005:** Given the registered server and two analysis-only workspaces, when a
  client calls `workspaces` and `analyze-work` with explicit IDs, then core report
  values equal the Codex and Claude results for the same input, and unknown IDs,
  arbitrary roots and execution without an operator grant refuse.

**REQ-005 Installer profile and host lists.** `agent-braid tooling install --host
pi` writes only receipt-owned entries; the host choices of the tooling and plugin
CLIs, `install.sh` and `integrations/agent-braid/hosts.json` name Pi; the harness
host registry lists Pi as unqualified, offline only.

- **SC-006:** Given a Pi configuration with foreign entries, when install, update
  and uninstall run, then only receipt-owned entries change, a modified owned entry
  refuses with a stable code, and the harness registry refuses any native Pi
  session.

**REQ-006 Read-only diagnosis.** `plugin doctor --host pi` reports, without writing,
skill and server collisions across the Pi discovery locations, duplicate skills that
ThinkRail imports from Claude or Codex plugins, and Agent Braid entries that a
multi-host configurator such as Gentle AI removed or rewrote.

- **SC-007:** Given fixtures with a shadowing skill, a ThinkRail-imported duplicate
  and a rewritten `agent-braid` server entry, when the doctor runs under a write
  monitor, then each finding is reported with its source path and no file changes.

**REQ-007 No added authority on a host without permissions.** Pi has no permission
layer by design. The package, its documentation and setup state that Agent Braid
adds no execution authority, that execution still needs an operator grant, and that
isolation is the operator's responsibility (for example ThinkRail worktrees or a
container).

- **SC-008:** Given the built package, when its skills, setup text and any
  extension are inspected, then none issues a grant, none claims a sandbox, and the
  no-permission-layer limit appears in setup and `docs/tooling/NATIVE_PLUGINS.md`.

**REQ-008 Native observation and conditional release.** The built candidate is
observed in Pi and ThinkRail in disposable profiles before release. The first
release that carries Pi follows alpha.10 and an explicit owner decision.

- **SC-009:** Given the candidate, when the observation runbook runs, then each row
  is observed, contradicted or `unobserved`; any contradiction blocks release; and
  the release record cites the owner decision. A no-go is a valid outcome.

## Owner decisions (open)

- **OD-1 Channel.** (a) Git install from `plugin-dist` with the bundled runtime, as
  SPEC-068 D3; (b) npm package; (c) local path only. Recommended: (a) first, since it
  adds no registry account or credential; npm only by a later decision.
- **OD-2 Skill names.** (a) unprefixed names as on the other hosts, with doctor
  warnings; (b) prefixed `agent-braid-*`. Recommended: (a), confirmed against the
  REQ-002 rows on collisions and ThinkRail imports.
- **OD-3 Fallback without Pi core MCP.** (a) skills plus the plugin `launch` CLI
  only; (b) a Pi extension that bridges MCP; (c) stop. Recommended: (a).
- **OD-4 Extension.** (a) no TypeScript extension in the first release; (b) a
  minimal extension. Recommended: (a); an extension runs in-process with Pi's full
  authority and adds a new trust boundary.
- **OD-5 Installer scopes.** User only, or user and project as SPEC-042. Recommended:
  both, if REQ-002 observes both locations.
- **OD-6 ADR.** Recommended: draft a Pi surface ADR (as ADR 0037 for OpenCode) after
  T004, cited by ADR 0044 portability tiers.
- **OD-7 Release.** Recommended: the first alpha after alpha.10 whose candidate
  passes REQ-008.

## Non-goals

Native harness sessions, Harbor evaluation (SPEC-084), any Pi model or provider
configuration, ACP integration (the ThinkRail–ACP relation is unverified), new MCP
tools, and changes to Gentle AI or its configuration.

## Risks

- **No permission layer (YOLO).** Any Pi tool call runs with the user's rights.
  Agent Braid cannot add a sandbox; REQ-007 states the limit.
- **Unverified facts.** Pi core MCP support, configuration paths and the ThinkRail
  import order are unverified. REQ-002 may contradict them; SC-003 handles it.
- **Gentle AI coexistence.** A configurator that rewrites host configuration may
  remove or duplicate Agent Braid entries. REQ-006 detects it; Agent Braid never
  edits Gentle AI-owned entries.
- **Double skills and drift.** ThinkRail imports Claude and Codex skills, so each
  skill may appear twice; ThinkRail is an incubator (v0.4.0), so pinned observations
  may expire.
- **Credentials.** A Pi run needs a model provider. The capture uses the owner's
  own sign-in in their terminal; no key enters chat, the repository or a file.

## Dependencies

- Precedent: [SPEC-068](../068-opencode-native-integration/spec.md),
  [ADR 0037](../../docs/adr/0037-opencode-native-plugin.md), the SPEC-048 Codex
  capture (#1421).
- Surface rules: [ADR 0044](../../docs/adr/0044-harness-portability-tiers-skill-surface.md),
  [ADR 0024](../../docs/adr/0024-native-ai-plugins.md),
  [ADR 0030](../../docs/adr/0030-native-plugin-surface-naming.md),
  [SPEC-042](../042-ai-tooling-packaging/spec.md) (receipts),
  [SPEC-047](../047-local-technical-telemetry/spec.md) (consent).
- Related: SPEC-080 (harness skill, optional), SPEC-084 (Pi evaluation via Harbor).

## References

- [Harnessing benchmark (2026-11)](../../docs/strategy/HARNESSING_BENCHMARK.md),
  [radar 2026-11-22](../../research/radar/2026-11-22-harnessing.json),
  [ADR 0044](../../docs/adr/0044-harness-portability-tiers-skill-surface.md)
- [Pi README](https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/README.md),
  [Pi packages](https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/packages.md),
  [ThinkRail](https://github.com/JetBrains/thinkrail),
  [Gentle AI](https://github.com/Gentleman-Programming/gentle-ai),
  [Zechner](https://mariozechner.at/posts/2025-11-30-pi-coding-agent/)
- [CONSTITUTION.md](../../CONSTITUTION.md), [GOVERNANCE.md](../../GOVERNANCE.md)
