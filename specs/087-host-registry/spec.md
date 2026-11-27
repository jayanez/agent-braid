# SPEC-087: Host registry

**Milestone:** Host parity (new milestone; owner decision of 2026-11-27, phase F7 of the
cleanup plan). First specification of the umbrella: SPEC-088 (Codex as a Braid Lightning
host) registers through this registry.

**Status:** draft, documentation only. Nothing is implemented, installed or published by
this specification's first PR. Code waits for owner approval of the spec and plan (T001).

## Purpose and scope

Host identity is spread over 63 literal collections in 34 Python files plus `hosts.json` (34 collections are product
code), with two spellings of the
Claude Code identifier (`claude` and `claude-code`).
Adding a host, for example Codex in Braid Lightning (SPEC-088) or Pi and ThinkRail
(SPEC-081), means finding and editing every list, and a missed list fails silently.
Counted on 2026-11-27 by an AST scan of `agent_braid/` and `scripts/` on `develop` at
2a524884; the sites and the 29 listed exceptions are in the
[plan](plan.md#host-sites-verified-2026-11-27).

This is engineering, not a research protocol. It adds one registry module that names
each supported host once, with its canonical identifier, its accepted input aliases, the
spelling each surface stores today, and the capabilities each existing per-feature host
set is made of. Each scattered list becomes a query on that registry that returns
exactly today's members. It adds no host and no capability.

Owner decisions (2026-11-27, binding): the canonical Claude identifier is
`claude-code`; `claude` stays an accepted input alias; stored and frozen data keep their
identifiers and are not migrated; the registry preserves behavior.

In scope: the registry module and its capability queries; alias normalization at every
host input; per-surface stored spellings; replacement of each listed site; a consistency
test against the packaged `hosts.json`; a guard test against new loose host lists;
contributor documentation of how a host is added.

Exclusions (each is a MUST NOT, stated with its REQ ID below):

- Changing the set of hosts or any host's capabilities (REQ-007).
- Rewriting stored or frozen data, or changing the bytes any surface writes (REQ-005,
  REQ-012).
- Changing `integrations/agent-braid/hosts.json` or any packaged asset byte (REQ-008).
- Moving per-host credentials, binary names, authentication labels or tool-name tables
  into the registry (REQ-009).
- Changing the harness qualification registry rows, its gates or its semantics, or
  treating a capability flag as qualification, an install observation or an
  authorization (REQ-013, REQ-014).
- Treating the viewer source labels `braid` and `other` as hosts (REQ-015).
- Reading the environment, files, the network or credentials in the registry (REQ-011).
- Editing SPEC-080, SPEC-081 or any closed specification (REQ-016).

## Authorities

[CONSTITUTION.md](../../CONSTITUTION.md) clause zero and Articles 0, 5, 13, 14, 19, 20;
[GOVERNANCE.md](../../GOVERNANCE.md); [ADR 0024](../../docs/adr/0024-native-ai-plugins.md)
(native plugin surface) and [ADR 0044](../../docs/adr/0044-harness-portability-tiers-skill-surface.md)
(harness portability tiers). No authority conflict found. Document hashes are kept in
`assurance.json`.

## Requirements and acceptance scenarios

**REQ-001 Owner review before code.** The spec and plan are reviewed before any code.

- **SC-001:** Given this spec and plan, when the owner reviews them, then each open
  question is decided or deferred in a dated record and the spec is approved, amended or
  rejected.

**REQ-002 One registry.** One module names every supported host. After the change, no
module in `agent_braid/` or `scripts/` outside the ten exception files of the plan
declares a collection of host identifiers; each site listed in the plan reads the
registry or is a feature-owned table pinned to it.

- **SC-002:** Given the registry and the sites listed in the plan, when a code search and
  the guard test (REQ-010) run, then every listed site obtains its hosts from the
  registry and none keeps a literal collection of host identifiers.

**REQ-003 Canonical identifiers.** The registry's closed set of canonical identifiers is
`codex`, `claude-code` and `opencode`. The canonical Claude identifier is `claude-code`.

- **SC-003:** Given the registry, when its identifiers are listed, then they are exactly
  `codex`, `claude-code` and `opencode`, in that order, with no other value.

**REQ-004 Input aliases.** Every host input accepts each canonical identifier and the
alias `claude` for the hosts the surface supports, and normalizes the alias to
`claude-code` before use. An unsupported or unknown value still ends in the surface's
existing refusal: its refusal code where it has one, and for argparse options exit
status 2 with no other output.

- **SC-004:** Given each surface that takes a host (the plugin CLI `--host`, the tooling
  CLI `--host`, the viewer `view env --host`, the Lightning configuration, the tooling
  measurement configuration),
  when `claude` and `claude-code` are supplied to a surface whose capability includes
  that host, then both are accepted and select the same host; when a host the surface
  does not support today is supplied (for example `codex` for Lightning), then the
  surface refuses as before; and when an unknown value is supplied, then the surface
  refuses with its existing code.

**REQ-005 Stored spelling preserved.** Each surface writes and reads the spelling it
writes and reads today. The registry exposes, per host and surface, that stored
spelling. For the same input, every output, receipt, record and JSON document is
byte-identical to the one produced before the change. The one exemption is argparse
usage, help and invalid-choice text, which may additionally list `claude-code`.

- **SC-005:** Given recorded fixtures for each surface listed in the plan's spelling
  table, when each runs before and after the change on the same input, then the output
  bytes are identical, except argparse usage, help and invalid-choice text.

**REQ-006 Capability queries keep today's membership.** Each existing per-feature host
set becomes a capability query on the registry that returns exactly today's members. A
capability is an ordered tuple fixed in the registry, and its order is the order of the
sites that observe order today (iterated, serialized, hashed or listed), as listed in
the plan's membership table. Membership-only sites do not constrain order.

- **SC-006:** Given the membership table recorded from `develop` at 2a524884, when each
  capability query is evaluated, then its members and order equal the recorded set; and
  a query for a capability a host does not have returns no such host.

**REQ-007 Behavior preserving.** The registry MUST NOT change the set of hosts or any
host's capabilities from today's.

- **SC-007:** Given the registry, when the union of hosts and the per-capability members
  are compared with the recorded membership table, then no host or capability differs;
  and a test that adds a host or capability to the registry without a matching table
  change fails.

**REQ-008 `hosts.json` unchanged and checked.** The packaged
`integrations/agent-braid/hosts.json` MUST NOT change. The registry declares its
spelling (`claude`, `codex`, `opencode`, in file order) as the stored spelling of the
`plugin-assets` surface, and a test fails when the file and the registry disagree.

- **SC-008:** Given the file at its recorded SHA-256 and the registry, when the
  consistency test runs, then it passes; and when the registry's stored spelling for that
  surface is altered, then it fails.

**REQ-009 Per-host data stays with its feature.** The registry MUST NOT hold per-host
credentials, credential variable names, binary names, authentication labels, origins,
parsers, tool-name or event tables, or harness qualification rows. Those tables stay in
their feature modules, and a test requires the key set of each table the plan lists
(`_PROFILES`, `_AUTH`, `_ORIGINS`, the model-identity tables, the Lightning runner
tables, `META_TOOLS`, `PARSERS`, `HOST_SUPPORT`, `_MODELED`) to equal the matching
capability query, in the surface's stored spelling.

- **SC-009:** Given each feature-owned table of the plan, when the key-set test runs,
  then each key set equals its capability query; and when a key is added to a table without the
  capability, then the test fails.

**REQ-010 Guard against loose host lists.** A test fails in CI when `agent_braid/` or
`scripts/` declares a literal collection of two or more host identifiers outside the
registry, except in the ten files the plan lists with a reason each. The guard reuses
the scan that records the baseline (T002).

- **SC-010:** Given the tree after the change, when the guard test runs, then it passes
  with only the ten listed exception files; and given a fixture module that declares
  `("codex", "claude-code")`, then the guard reports it.

**REQ-011 Pure registry.** Importing or querying the registry MUST NOT read the
environment, files, the network, the clock or credentials. It uses only the standard
library.

- **SC-011:** Given an import of the registry under a process with file, network and
  environment access traced, when it loads and answers every query, then it performs no
  such access and its answers are identical on repeat.

**REQ-012 No migration of frozen data.** The change MUST NOT rewrite stored evidence,
receipts, qualification records, frozen assurance records or any record written under an
earlier format.

- **SC-012:** Given the frozen fixtures and the committed evidence directories, when the
  change is applied, then `git diff` shows no change to any of them and the existing
  verifiers still accept them.

**REQ-013 Harness qualification registry untouched.** The registry MUST NOT change the
harness qualification registry rows, the native qualification gate set, their
`observedBuild` and `qualification` fields or their refusals. The gate set becomes a
capability query with its current members (`claude-code`, `codex`; stored spelling
`claude`, `codex`); the inventory set keeps `opencode` as inventory only.

- **SC-013:** Given the harness registry and gate tests, when they run unchanged after
  the change, then they pass; and the gate query returns `claude-code` and `codex`
  without `opencode`.

**REQ-014 A capability is not an authorization.** A capability flag MUST NOT be read as
qualification, an install observation, a measurement or an authorization to run. Nothing
in the registry grants execution; no result of this feature carries
`executionAuthorization: true`.

- **SC-014:** Given the registry and its documentation, when they are inspected, then no
  query or field named or documented as qualification, observation or authorization
  exists, and every command result touched by the change that carries
  `executionAuthorization` keeps the boolean `false`.

**REQ-015 Viewer labels are not hosts.** The viewer source labels `braid` and `other`
MUST NOT be registered as hosts. They stay in the viewer's own vocabulary.

- **SC-015:** Given the viewer vocabulary and the registry, when both are listed, then
  `braid` and `other` appear only in the viewer vocabulary and the registry identifiers
  are exactly those of REQ-003.

**REQ-016 No other specification edited.** This specification's change set MUST NOT edit
SPEC-080, SPEC-081, a closed specification, the Constitution or its replica. Its
registry terms follow those of SPEC-080 and SPEC-081 and say so.

- **SC-016:** Given the change set, when its changed paths are listed, then no path is in
  `specs/` other than `specs/087-host-registry/`, none is `CONSTITUTION.md` or its
  replica, and no closed specification changes.

**REQ-017 Documented extension path.** (Proposed by the author as the proof of OD-4;
OD-5 asks the owner to confirm it.) The contributor documentation states how a host
is added: one registry entry, its capability flags, its stored spellings and the
feature-owned tables of REQ-009. A test using a fake host proves that adding it needs no
edit to any other host list.

- **SC-017:** Given a fake host added to a copy of the registry, when the guard and
  key-set tests run, then they report exactly the feature-owned tables that lack an
  entry for it and no loose list.

## Non-functional requirements

- Deterministic: the registry's answers are identical on every call and in every
  process (REQ-011).
- No new dependency: standard library only (REQ-011).
- Compatibility: byte-identical outputs, receipts and packaged assets (REQ-005,
  REQ-008, REQ-012).
- Reviewable: each capability's members are stated in a table that the tests compare
  against (REQ-006).
- Performance and size limits: no requirement applies beyond import without side
  effects; the registry is a constant table of three entries.

## Security and privacy

- The registry MUST NOT read or hold credentials, credential variable names, tokens or
  personal data (REQ-009, REQ-011).
- No telemetry, network access or file access is added (REQ-011).
- A capability flag is not an authorization; the registry grants no authority
  (REQ-014).
- No frozen or stored record is rewritten (REQ-012).

## Terminology

- **Host:** an AI coding tool that Agent Braid integrates with. Registered hosts are
  `codex`, `claude-code` and `opencode`; Pi and ThinkRail are not registered by this
  specification (REQ-003, REQ-007).
- **Canonical identifier:** the registry's identifier for a host. Allowed values:
  `codex`, `claude-code`, `opencode` (REQ-003).
- **Alias:** an accepted input spelling that normalizes to a canonical identifier. The
  only allowed value is `claude`, for `claude-code` (REQ-004).
- **Stored spelling:** the spelling a surface writes or reads today for a host
  (REQ-005). Allowed surface values: `plugin-assets`, `harness`, `viewer`,
  `host-events`, `lightning`, `tooling`.
- **Capability:** a named, closed property of a host that today's code expresses as
  membership in a per-feature list. Allowed values: `plugin-assets`,
  `tooling-measurement`, `host-events`, `lightning-run`,
  `lightning-tool-classes`, `harness-gated`, `harness-inventory`, `viewer-hosts`; T001
  may rename them (REQ-006).
- **Capability query:** a registry function that returns the hosts having a capability,
  in a fixed order (REQ-006).
- **Harness qualification registry:** the existing records in `harness_hosts.py` and
  `harness_components.py` with `observedBuild` and `qualification`, named "host
  registry" in SPEC-080 and SPEC-081. It is not this registry (REQ-013).
- **Feature-owned table:** a per-host table that stays in its feature module (REQ-009).
- Shared terms follow the root [TERMINOLOGY.md](../../TERMINOLOGY.md).

## Scientific boundaries and compatibility

Engineering, not a research protocol; no hypothesis.

- **Domain:** host identifiers and their capability memberships in `agent_braid/` and
  `scripts/` at the recorded commit.
- **Observation contract:** the membership table and the per-surface outputs recorded
  from `develop` at 2a524884 before the change; equality of bytes and sets after it.
- **Execution contract:** none. The registry runs no host, grants nothing and writes no
  record.
- **Limits:** equality with recorded membership shows the change preserved behavior at
  that commit, not that today's memberships are right. The registry does not observe
  that any host works.
- **Compatibility:** additive module; existing surfaces keep their inputs, outputs and
  stored data. Rollback restores the literal lists.

## Owner decisions

The owner answered OD-1 to OD-4 on 2026-11-27 through four AskUserQuestion prompts in the
author session (Spanish, with options, examples, risks and a recommendation), choosing
the recommended option each time. The orchestrator's binding decisions of the same day
(canonical `claude-code`, `claude` as input alias, no migration of frozen data, behavior
preserving, Host parity milestone, priority before SPEC-088) are the premise of OD-1 and
OD-2. OD-5 is not decided.

- **OD-1 `hosts.json`.** Decided: leave the file unchanged and check it against the
  registry. Rejected: change it to `claude-code`, which changes packaged bytes,
  provenance and installed-version verification (REQ-008).
- **OD-2 Output spelling.** Decided: inputs accept `claude` and `claude-code` and
  normalize; each surface keeps writing its current spelling (REQ-004, REQ-005).
  Rejected: write `claude-code` everywhere, which breaks frozen formats.
- **OD-3 Per-host data.** Decided: credentials, binaries, authentication labels and
  tool-name tables stay in their feature modules (REQ-009). Rejected: put them in the
  registry.
- **OD-4 Guard.** Decided: a CI test fails on new loose host lists, with an explicit
  exception list (REQ-010). Rejected: convention only.
- **OD-5 Exceptions and fake-host proof (open).** The ten exception files of the plan
  and the fake-host test of REQ-017 are the author's proposals, derived from the AST scan
  and the closed or non-host nature of each file; the owner has not answered them. Options
  for the SPEC-069 drivers: keep them as exceptions (recommended: closed evidence tied to
  recorded held-out runs, SPEC-088 migrates what it touches) or migrate them here (larger
  diff, risk to recorded evidence). Owner confirms in T001.

## Risks and assumptions

- Risk: an alias normalized too early changes a stored value and breaks a frozen
  verifier (REQ-005, T004).
- Risk: the guard test flags an unrelated literal and its exception list grows
  (REQ-010, T007).
- Risk: a capability name is read as a qualification claim (REQ-014, T001).
- Risk: SPEC-088 and SPEC-081 land before this registry and add their own lists
  (REQ-002, T007).
- Risk: an argparse `choices` change alters help or invalid-choice text that a test or a
  document quotes (REQ-004, T004).
- Risk: the AST scan misses a host list built dynamically or from another constant
  (REQ-010, T007).
- Assumption: every module and script that lists hosts can import the registry from the
  same package (REQ-002, T003).
- Assumption: the membership table recorded at 2a524884 is the behavior to preserve
  (REQ-006, T002).
- Assumption: the viewer `HOSTS` tuple is the only host-bearing part of the viewer's
  vocabulary (REQ-015, T006).

## Exit criteria

Verification is complete when the obtained evidence listed in
[the validation plan](validation-plan.md) exists for procedures 001 to 017, which map to
SC-001 to SC-017 and to the tasks in [tasks.md](tasks.md) that name them, with the
before and after differential records of T010 attached. Passing checks are not approval.

## Open questions

- OD-5: confirm the ten exception files and the fake-host test (REQ-017), or move the
  SPEC-069 drivers into scope. Owner: the founder, at T001.

## Dependencies

- Consumers: SPEC-088 (Codex as a Braid Lightning host) registers through this registry
  and depends on it; SPEC-081 (Pi and ThinkRail) registers through it later.
- Read, not edited: SPEC-080 and SPEC-081 (term "host registry"), SPEC-052 and SPEC-065
  (harness qualification), SPEC-060 and SPEC-068 (packaged plugin and OpenCode),
  SPEC-061 (viewer), SPEC-069 and SPEC-076 (Lightning), SPEC-047 (telemetry events).

## References

- [CONSTITUTION.md](../../CONSTITUTION.md), [GOVERNANCE.md](../../GOVERNANCE.md).
- [Plan](plan.md), [tasks](tasks.md), [validation plan](validation-plan.md).
- [Native plugin documentation](../../docs/tooling/NATIVE_PLUGINS.md),
  [hosts](../../docs/tooling/HOSTS.md).
