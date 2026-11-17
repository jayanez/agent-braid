# SPEC-077: Read-only harness MCP surface

**Milestone:** HAR.3 — Braid Harness adaptation and integration (orchestrator
decision 2026-11-16: HAR.3 covers opt-in product integration of the harness. Owner
decision D3 of [SPEC-050](../050-braid-harness-adaptation/owner-decisions-20261113.md)
named M4.8, which is the AIM request-authoring milestone, a loose fit; D3's
requirement of its own versioned contract stands).

**Status:** draft. Contract only; nothing is implemented or published by this
specification's first PR. Publication is conditional (REQ-010).

## Purpose and scope

The four SPEC-049 T009 advisory views of the experimental `agent-braid harness`
CLI (`capabilities`, `registry-status`, `evaluation-summary`, `evidence`) are only
reachable from a shell today. A host model (Claude Code, Codex, OpenCode) that wants
to tell the operator what the harness laboratory records say has to run the CLI. This
specification drafts a versioned, read-only MCP contract,
`agent-braid-harness-mcp/v0.1`, that exposes exactly those four views through the
native plugin MCP facade, and the gate that decides whether it is ever published.

This is engineering, not a research protocol. It makes no claim that the harness is
useful; that question belongs to SPEC-049 T014 and the D7 ADR.

In scope:

- the contract [contracts/harness-mcp-readonly.md](contracts/harness-mcp-readonly.md):
  four tools, their flat input schemas, the schema text each tool carries in its
  description, workspace-relative path resolution, bounded output, refusals with a
  JSON Pointer, and `executionAuthorization: false` on every result;
- the versioning decision (plugin facade, additive under `agent-braid-plugin/v0.2`;
  portable `agent-braid-tooling/v0.2` unchanged, so no `v0.3` bump and no coupling to
  issue #771);
- a held-out host validity test in Claude Code, Codex and OpenCode before publication;
- the publication gate, a draft ADR ([ADR 0043](../../docs/adr/0043-harness-mcp-readonly-surface.md),
  Proposed) and an independent Codex review packet of the contract.

Exclusions (each is a MUST NOT of the contract, not a deferral):

- Native execution over MCP: no native host launch, no laboratory attempt, no
  containment probe, no `prepare`, `status`, `recover-inspect`, `inspect`,
  `validate` or `compare` tool. The MCP server runs as the operator user and cannot
  `sudo` the root-owned launcher; a launch would change the SPEC-065 environment hash
  and spend subscription quota; host tool approval is not an operator grant (owner
  decision, 2026-11-16).
- Grants, reservations, admissions, profile promotion, activation, registry writes
  or any other effect. The four tools only read.
- Ordinary-use activation of the harness (SPEC-049 T007) and any change to
  `docs/tooling/HARNESSING.md` claims before publication.
- New tools on the portable `agent-braid-tooling` server.
- Editing global host instructions, host configuration or permissions.

## Authorities

- [CONSTITUTION.md](../../CONSTITUTION.md): clause zero; Articles 5 (effects),
  13 and 14 (evidence, not verdicts), 15 (tool protocols carry effect semantics),
  19, 20 (analysis and execution are separate products), 23 and 24.
- [GOVERNANCE.md](../../GOVERNANCE.md).
- [SPEC-049](../049-harness-evaluation-learning/spec.md) SC-008 and task T009 (a
  plugin/MCP extension needs a versioned contract and its own review; no new MCP
  execution surface is implied).
- [SPEC-050 owner decisions](../050-braid-harness-adaptation/owner-decisions-20261113.md)
  D3 (CLI access, own versioned contract under M4.8) and D7 (activation policy and ADR
  only after SPEC-049 T014).
- [ADR 0030](../../docs/adr/0030-native-plugin-surface-naming.md) (plugin surface
  naming, no prompts), [ADR 0031](../../docs/adr/0031-portable-prompt-names.md)
  (portable surface `v0.2`, alias removal in `v0.3`),
  [ADR 0035](../../docs/adr/0035-native-claude-laboratory-containment.md) (native
  containment), [ADR 0038](../../docs/adr/0038-analyze-work-request-contract.md)
  (refusal form, schema delivery in the tool, description cap).
- [SPEC-060 interface delta](../060-portable-prompt-names/contracts/interface-delta.md)
  (the `v0.2` tool set is unchanged from `v0.1`).
- [docs/tooling/HARNESSING.md](../../docs/tooling/HARNESSING.md) and
  `agent_braid/harness_cli.py` (the CLI views this contract mirrors).
- Issue #1343 (analyze-work request validity below D4; HELD-04 fails on every host):
  input to the argument design and the held-out test.
- Issue #771 (SPEC-060 T011, alias removal under `agent-braid-tooling/v0.3`).

## Clarifications

Owner decisions of 2026-11-16 (relayed by the orchestrating session): draft the
contract now, publish only after SPEC-049 T014; native execution over MCP is
excluded. SPEC-044 T005 (CLI vs MCP comparison) never ran, so no empirical CLI-vs-MCP
baseline exists; the surface choice rests on the counterfactual analysis, not data.
Open owner decisions are listed under "Evidence and unresolved questions".

## Requirements and acceptance scenarios

**REQ-001 Owner contract review.** The contract, the versioning decision and the
publication gate are reviewed by the owner before implementation.

- **SC-001:** Given this spec, plan, contract and ADR 0043, when the owner reviews
  them, then OD-1 to OD-6 are decided or deferred in a dated record and the contract
  is accepted, amended or rejected.

**REQ-002 Exact tool set.** The surface lists exactly four tools,
`harness-capabilities`, `harness-registry-status`, `harness-evaluation-summary` and
`harness-evidence`, each mapped to the CLI view of the same suffix. No other harness
command is reachable over MCP.

- **SC-002:** Given a plugin server with a registered workspace, when tools are
  listed, then exactly those four harness names appear in addition to the existing
  plugin tools, and a call naming any other harness command (`prepare`, `status`,
  `recover-inspect`, `inspect`, `validate`, `compare`) is refused as an unknown tool.

**REQ-003 No authority and no effects.** Every result, success or refusal, carries
`executionAuthorization: false`. A call writes nothing, holds no lock, reads no clock,
host, model or network, launches nothing and never promotes, activates or grants.

- **SC-003:** Given every tool and every refusal path, when called under a
  filesystem write monitor and with network and subprocess creation denied, then no
  file is created or modified, no subprocess starts, no socket opens, and each result
  has `executionAuthorization` exactly `false`.

**REQ-004 Trivial, flat arguments with the schema in the description.** Each input
schema is a flat object with `additionalProperties: false` and at most three
properties (`workspaceId`, one path, and for `harness-evaluation-summary` an optional
`sha256`). Each tool description contains its compact input schema text and one
example call, within 2,048 UTF-8 bytes.

- **SC-004:** Given the tool listing, when each definition is inspected, then its
  schema is flat with the stated properties, its description embeds the same schema
  text byte-for-byte as the published contract, and the description is at most
  2,048 bytes.

**REQ-005 Workspace-bound paths.** A path argument is a workspace-relative POSIX
path resolved under the registered workspace's source root without following links.
Absolute paths, `..`, backslashes, empty segments and NUL refuse structurally. A
missing path, a link, a non-regular file and a path outside the root return the same
semantic refusal.

- **SC-005:** Given paths that are absolute, contain `..`, traverse a symlinked
  directory, name a symlink, a FIFO, a missing file or a file outside the root, when
  a tool is called, then each refuses, and the missing, link, special and outside
  cases are byte-identical refusals.

**REQ-006 CLI parity.** For the same input bytes, the `result` object of a successful
call equals the CLI's stdout object minus `status` and `executionAuthorization`, and
a refused call carries the CLI's reason code.

- **SC-006:** Given the committed SPEC-049 T009 fixtures and their negative
  controls, when each is run through the CLI and the MCP tool, then the result
  objects and reason codes are equal (differential test).

**REQ-007 Bounded output.** Inputs keep the CLI bounds (1 MiB record, 256 evidence
files, 1,024 entries, depth 4). A serialized tool result is at most 65,536 bytes; a
larger one is refused with `output-too-large` and the observed counts, never
silently truncated.

- **SC-007:** Given inputs at, just under and just over each bound, when called,
  then results under the cap succeed and results over it refuse with
  `output-too-large`; no truncated result is returned.

**REQ-008 Refusals with a JSON Pointer.** A structural refusal names the failing
argument as an RFC 6901 JSON Pointer into the call arguments and the expected form.
A semantic refusal carries a fixed reason code and the pointer of the argument that
carried the input (empty string when none). Argument values are never echoed; unknown
keys are replaced by `<key:digest8>`; messages stay within 1,024 characters.

- **SC-008:** Given malformed arguments (wrong type, unknown key, bad hash, bad
  path) and semantically invalid inputs, when called, then each refusal has the
  expected pointer and code, contains none of the submitted values, and is at most
  1,024 characters.

**REQ-009 Held-out host validity.** Before publication, a held-out prompt set,
frozen by hash before any run and never used for tuning, is run in Claude Code, Codex
and OpenCode with the plugin installed. Per host, at least 8 of 10 prompts are valid
at the first attempt and 10 of 10 within one refusal-guided retry (the SPEC-069 D4
target, unless the owner records a revised target under OD-2). The set includes
prompts that ask for execution, promotion or a grant; a valid answer there calls no
harness tool for the effect and says the surface has no such capability.

- **SC-009:** Given the frozen set and an automated driver, when 10 prompts × 3
  repetitions run per host, then per-host first-attempt validity with Wilson 95%
  intervals, per-prompt outcomes and failure signatures are recorded, and a miss is
  reported as a negative result, not tuned away on the same set.

**REQ-010 Conditional publication.** The surface is published only when all hold:
(a) SPEC-049 T014 has recorded results; (b) the D7 ADR does not close the harness as
experimental; (c) REQ-009 passes; (d) the Codex contract review's confirmed findings
are fixed; (e) the owner accepts the implemented candidate. If (a) or (b) fails, this
specification closes with a recorded no-publish outcome; that is a valid result.

- **SC-010:** Given the gate inputs, when the publication decision is recorded, then
  it cites each condition's evidence, and a failing condition yields "not published"
  with the implementation left unreleased.

## Scientific boundaries and compatibility

- **Hypotheses.** H1: tools with trivial flat arguments and the schema in the
  description reach the D4 validity target on all three hosts, unlike `analyze-work`
  (#1343). This is a hypothesis; REQ-009 may refute it.
- **Assumptions.** The plugin facade keeps requiring an explicit registered
  `workspaceId`; the CLI views stay as merged in SPEC-049 T009.
- **Domain.** The four advisory views over local files in a registered workspace.
- **Observation contract.** What the T003 report, the T013 registry and an evidence
  directory say, with the CLI's stated limits; hashes bind bytes, not authenticity.
- **Execution contract.** None. The surface carries no execution authority.
- **Compatibility.** Additive to `agent-braid-plugin/v0.2` under OD-1 (recommended);
  `agent-braid-tooling/v0.1` envelopes and `v0.2` surface unchanged; SPEC-047
  telemetry names follow OD-4. Rollback is reinstalling the previous plugin release.

## Evidence and unresolved questions

Planned and obtained evidence are separate in [assurance.json](assurance.json).
Owner decisions the contract needs:

- **OD-1 Surface and version.** Recommended: plugin facade only, additive under
  `agent-braid-plugin/v0.2`, own result contract `agent-braid-harness-mcp/v0.1`; no
  `agent-braid-tooling/v0.3`. Alternative: also on the portable server, which changes
  its fixed `v0.2` tool set and needs `v0.3`, bundled with the #771 alias removal so
  the bump happens once.
- **OD-2 Validity target.** Keep the SPEC-069 D4 target (recommended) or record a
  revised one with its reason before the set is frozen.
- **OD-3 Output cap.** 65,536 bytes with refusal (recommended) versus pagination.
- **OD-4 Telemetry.** SPEC-047 operation names are a closed enum; unknown tools
  count as `other`. Recommended: add the four names in the same batch-schema change
  as the harness CLI telemetry track, so the schema bumps once.
- **OD-5 Release.** Which release carries the surface if the gate passes.
- **OD-6 ADR 0043.** Stays Proposed until the gate; accepted or rejected with the
  publication decision.
