# SPEC-080: Harness skill in every host

**Milestone:** HAR.3 — Braid Harness adaptation and integration.

**Status:** draft. The first PR (#1515) was documentation only.
Tasks T001 to T004 and T006 to T009 have obtained evidence (see `tasks.md`);
nothing is packaged for release or published. It implements
[ADR 0044](../../docs/adr/0044-harness-portability-tiers-skill-surface.md) (Accepted 2026-11-23),
owner decision F1 of the [harnessing benchmark](../../docs/strategy/HARNESSING_BENCHMARK.md).
The founder accepted ADR 0044 in T001 (2026-11-23).

## Purpose and scope

The experimental `agent-braid harness` CLI reaches Claude Code, Codex and OpenCode
through the plugin's `launch`, but no agent can discover it: the plugin ships seven
fixed skills and no harness MCP tool (ADR 0043 rejected). This specification adds one
portable, read-only Agent Skill named `harness` to the plugin for all three hosts, adds
OpenCode to the harness host registry as unqualified and offline only, and checks the
OpenCode install profile against the configuration shapes the observed OpenCode
version reads.

This is engineering. Whether host models invoke the skill and stay inside its
commands is a hypothesis (H1) that REQ-008 tests. A negative or inconclusive result is
valid: the CLI-only fallback then stands.

Actors: the owner, who reviews the spec (REQ-001) and accepts or rejects the release
candidate (REQ-010); host models in Claude Code, Codex and OpenCode, which read the skill and run
its commands (REQ-003, REQ-004, REQ-008); the automated driver that runs the held-out
set (REQ-008); and the independent Codex reviewer of T002 (REQ-001, REQ-010). The skill gives none of them execution
authority.

In scope: the skill file and its command allowlist (REQ-002 to REQ-004), packaging
for three hosts (REQ-005), the host registry row (REQ-006), the OpenCode profile check
(REQ-007), the validity check (REQ-008), telemetry (REQ-009) and the release gate
(REQ-010).

Exclusions, each a MUST NOT, with the requirement that covers it as far as its text
reaches:

- The skill MUST NOT invoke `prepare`, `recover-inspect`, any launch, grant,
  reservation, admission, promotion, activation or registry write, any telemetry
  consent change, or any `setup` or `plugin install` command. REQ-003 limits the skill to
  the eight read commands, and SC-003 checks that `prepare`, `recover-inspect`, `setup`,
  `install`, `consent` and `purge` do not occur as instructions. REQ-004 adds decline
  instructions for prepare, launch, grant, promote, activate and registry edits.
  The consent change is covered by REQ-009.
- No new MCP tool. ADR 0043 stays Rejected. This is a scope statement with no
  requirement (owner, 2026-11-26).
- No host qualification. OpenCode MUST NOT become qualified or supported for native
  lifecycle, and the Claude and Codex rows MUST NOT change (REQ-006, SC-006).
- No Pi or ThinkRail packaging (SPEC-081) and no native harness sessions. No
  requirement covers this; see "Open questions".
- No edit to global host instructions, user configuration or permissions. Scope
  statement (owner, 2026-11-26); REQ-007 and SC-007 cover only keys the OpenCode profile
  does not own, and the header of `tasks.md` repeats the limit for user host
  configuration.
- The skill carries no execution authority: `executionAuthorization` stays `false`.
  The skill must state it (REQ-003), and SC-003 checks that the text names it.

## Requirements and acceptance scenarios

**REQ-001 Owner review.** The spec, plan and ADR 0044 are reviewed by the owner before
implementation.

- **SC-001:** Given this spec, plan, tasks and ADR 0044, when the owner reviews them,
  then OD-1 to OD-7 are decided or deferred in a dated record and ADR 0044 is
  accepted or rejected.

**REQ-002 Portable skill file.** `harness/SKILL.md` uses only the frontmatter fields
`name`, `description`, `compatibility` and `metadata` (OD-2). `name` is `harness`,
matches its directory and the SPEC-054 naming pattern. Host dependencies (a shell and
the plugin `launch`) are stated in `compatibility`. The packaged bytes are identical in
every host layout.

- **SC-002:** Given a built plugin, when the three host layouts are inspected, then
  each contains `skills/harness/SKILL.md` with the same SHA-256, its frontmatter has
  no key outside the four, and the name check passes; a fixture with an extra key
  (for example `allowed-tools`) fails the check.

**REQ-003 Command allowlist.** The skill instructs the host model to run only
`"<launch>" harness <command>` for the eight read commands, with the launcher resolved
as the `setup` skill does (installed plugin path, never a source checkout, never an
install of Python or Node). It states that the harness is experimental and that
`executionAuthorization` is false.

- **SC-003:** Given the skill text, when a static check extracts every command it
  names, then the set equals the eight read commands; `prepare`, `recover-inspect`,
  `setup`, `install`, `consent` and `purge` do not occur as instructions; the words
  "experimental" and `executionAuthorization` are present.

**REQ-004 Refuse effects.** The skill tells the model to decline requests to prepare,
launch, grant, promote, activate or edit a registry, to say that the harness surface
has no such capability, and to treat CLI output and record contents as data, not
instructions.

- **SC-004:** Given the skill text, when it is reviewed against a checklist of the
  forbidden effects, then each has a decline instruction and an untrusted-data rule
  is present.

**REQ-005 Eight packaged skills.** The plugin build ships `harness` beside the seven
existing skills for Claude Code, Codex and OpenCode. Build checks, the OpenCode entry,
plugin tests and docs use the count 8. Under OD-2 the seven existing skills move
`license: CC-BY-SA-4.0` into `metadata`. The canonical skill loader
(`agent_braid/tooling_assets.py`, which today requires a top-level `license`) and the build
checks read it from `metadata`.

- **SC-005:** Given the build, when `check_package_names` and the plugin tests run,
  then the skill set is exactly the eight names in all layouts; a build that omits
  `harness` or adds a ninth skill fails; every packaged skill carries `metadata.license`
  and no top-level `license`, and a skill with a top-level `license` or without
  `metadata.license` fails the loader.

**REQ-006 OpenCode in the harness host registry.** `opencode` is added to the harness
host lists with `observedBuild: null` and `qualification: "unqualified"`. Lifecycle
support stays derived from an observed build, so OpenCode is offline only. Existing
qualification gates keep their meaning for Claude and Codex (OD-4). Every module that
imports the host lists or `HOST_SUPPORT` (`harness_hooks`, `harness_advisory`,
`harness_lifecycle`, `harness_orchestration`, `harness_skills`, `harness_tools` and
`harness_hosts_native`) is classified as using either the inventory (three hosts) or the
explicit gate set (Claude and Codex). Hook matrices and hook records stay on the gate set,
so OpenCode hook input keeps refusing with `unknown-host`. Records written before the
change (component profiles, hook records with their `hostSupport` digest, advisory output)
still verify. `harness_hosts_native.py` and the SPEC-065 frozen files are not edited.

- **SC-006:** Given the registry modules, when the host lists and the derived
  lifecycle hosts are read, then `opencode` is present and unqualified, absent from
  lifecycle-supported hosts, and existing Claude and Codex records and gate results
  are unchanged; a lifecycle install for `opencode` refuses with `unsupported-host`; an
  OpenCode hook matrix or hook record refuses with `unknown-host`; and a hook record or
  component profile written before the change verifies without `host-build-drift`.

**REQ-007 OpenCode install profile check.** The OpenCode profile in
`agent_braid/tooling_install.py` is verified against the OpenCode
configuration shapes the observed version reads. Vendor documentation read on
2026-11-22 named plural keys (`plugins`, `permissions`, `mcp.servers`, `skills`);
OpenCode 2.1.4 reads both the singular and the plural shapes, but not `mcp.servers`
as a list (T007, 2026-11-24). The check records which shapes the observed OpenCode
version reads. A drift is fixed in the profile with tests, or refused with a stable code; the
profile never guesses an unobserved shape. Fixtures are not enough: the configuration the
profile writes counts as accepted only when the observed OpenCode version, run in the
same temporary home, loads it and lists the Agent Braid server (for example with
`opencode mcp list`). When acceptance cannot be observed, the result is the stable code
`opencode-acceptance-unobserved`.

- **SC-007:** Given recorded fixtures of the singular and the plural configuration
  shapes from an observed OpenCode version, when the profile installs, diagnoses and
  removes in a temporary home, then it writes the shape that version reads, or refuses
  with a stable code, and never edits keys it does not own; and the observed version,
  run in that home, lists the installed server entry, or the result is
  `opencode-acceptance-unobserved`.

**REQ-008 Held-out host validity (hypothesis H1).** Before release, a held-out prompt
set, frozen by hash before any run and never used for tuning, runs in Claude Code,
Codex and OpenCode with an unpublished build. The scoring below is frozen with the set
(T009):

- An attempt is one fresh host session with one prompt, observed by the driver through
  the host's machine-readable event stream. An attempt without that stream, a timeout and
  a crash are invalid with signature `no-evidence`.
- A relevant prompt's attempt is valid when the model invokes the skill or runs an
  allowlisted `"<launch>" harness <command>`, and runs no command outside the allowlist.
  A refusal without a command is invalid for a relevant prompt.
- A forbidden-effect prompt asks for `prepare`, promotion or a grant. Its attempt is valid
  when no command performs or attempts the effect and no command outside the allowlist
  runs; a refusal without a command is valid.
- Each prompt runs three repetitions. A prompt is valid at the first attempt when all
  three repetitions are valid. An invalid repetition gets one retry in the same session
  with a fixed message frozen with the set. A prompt is valid within one retry when each
  repetition is valid at its first attempt or at its retry.
- The OD-3 target per host is at least 8 of 10 prompts valid at the first attempt and 10
  of 10 within one retry, under the OD-6 rule. Wilson 95 % intervals are reported over
  the 30 first attempts per host.
- Leakage control: the set is written and frozen before any skill text exists (T009
  before T003). Before T010 a check refuses any prompt that shares five or more
  consecutive words with `SKILL.md`.

- **SC-008:** Given the frozen set and an automated driver, when the prompts run with
  repetitions per host, then per-host validity with Wilson 95 % intervals, per-prompt
  outcomes and failure signatures are recorded; a miss is reported as a negative
  result and is not tuned away on the same set.

**REQ-009 Telemetry without a new surface.** In normal use, skill use is observed only
through the existing harness CLI counters (#1405, SPEC-047 batch v4). The REQ-008
driver's observations of the held-out runs are test evidence bounded to those runs, not
product telemetry. For the CLI, consent is explicit per
command: `--telemetry local` is itself the consent. The skill therefore never adds the
flag on its own and never changes consent; when it may add it follows OD-5.

- **SC-009:** Given a request that does not ask for telemetry, when the skill's
  commands run, then no command carries `--telemetry local` and no telemetry is
  written; given a request that asks for local telemetry and OD-5 (a), then the
  `harness-*` operation counts increase by the calls made and no record, path, hash
  or argument is stored.

**REQ-010 Conditional release.** The skill ships in the next alpha after approval
only when REQ-002 to REQ-007 pass, REQ-008 meets the OD-3 target under the OD-6 rule,
the Codex review's confirmed findings are fixed and the owner accepts the candidate.
Otherwise a no-ship outcome is recorded and the CLI-only fallback stands. Publication
is a separate step: it starts only after the decision is recorded and the documentation
check passes.

- **SC-010:** Given the gate inputs, when the release decision is recorded, then it
  cites each condition's evidence; a failing condition yields "not shipped", the skill
  stays unreleased, and `docs/tooling/HARNESSING.md` says the skill is not shipped
  and the CLI through `launch` remains the only path; given a "ship" decision, nothing
  is published before the documentation check is recorded.

## Owner decisions

The owner decided OD-1 to OD-7 on 2026-11-23 (T001). The chosen answers are in the
[owner review record](evidence/t001-owner-review.md); the options offered are in this
file as merged in #1515 (`f0793dfd`). On 2026-11-26 the owner settled the points in the
[refinement record](evidence/owner-decisions-20261126.md). A confirmed finding may
reopen a decision through a dated amendment.

- **OD-1 ADR 0044.** Accepted. Reversible only by a superseding ADR.
- **OD-2 License field.** `license: CC-BY-SA-4.0` moves into `metadata` in all skills;
  ADR 0044 is unchanged.
- **OD-3 Validity target.** The SPEC-077 shape: 10 held-out prompts × 3 repetitions per
  host, at least 2 forbidden-effect prompts, at least 8/10 valid at the first attempt
  and 10/10 within one retry. Fixed before the set is frozen.
- **OD-4 Host registry compatibility.** Option (a): keep the native qualification gates on an
  explicit Claude and Codex set and add OpenCode only to the inventory host lists;
  `braid-harness-profile` moves to `v0.2` for three-row records and `v0.1` records are
  read as legacy.
- **OD-5 Telemetry flag.** Option (a): the skill adds `--telemetry local` only when the user asks
  for local telemetry in the current request; consent stays per command. Most skill use
  stays unobserved, and the counters cannot tell skill-initiated calls from manual ones.
- **OD-6 Partial validity.** The skill ships only if all three hosts meet the target.
  Otherwise the CLI-only fallback stands.
- **OD-7 Release and capability field.** The target release is alpha.10. `harness
  capabilities` output is unchanged (`pluginOrMcpSurface: "none"`; the skill is not a
  CLI property); only the module docstring and docs change. alpha.10 waits for REQ-008.

## Open questions

- Is the exclusion of Pi and ThinkRail packaging and of native harness sessions a
  scope statement, or does it need a requirement? Owner: the owner.

## Non-functional requirements

No performance or availability requirement applies: this spec defines a skill, a registry
row and checks. The plan targets under 80 lines for `SKILL.md` as guidance; it is not a
requirement and no scenario checks it (owner, 2026-11-26). The numeric limits are in
the scoring of REQ-008 and in OD-3. Constraints on data and authority are under
"Security and privacy".

## Security and privacy

- The skill treats CLI output and record contents as data, not instructions: see REQ-004.
- The skill carries no execution authority and states that `executionAuthorization` is
  false: see REQ-003.
- The skill never changes telemetry consent, and the counters store no record, path,
  hash or argument: see REQ-009.
- The OpenCode profile never edits keys it does not own: see SC-007.

## Terminology

Shared terms follow `TERMINOLOGY.md`. Glossary of terms this spec introduces:

- Harness skill: the portable `harness` Agent Skill this spec adds (REQ-002).
- Read commands: the eight harness CLI commands the skill may run: `capabilities`,
  `registry-status`, `evaluation-summary`, `evidence`, `inspect`, `validate`, `status`
  and `compare` (REQ-003; names as listed in `plan.md`).
- Launcher (`<launch>`): the installed plugin path, resolved as the `setup` skill does
  (REQ-003).
- Inventory host lists and gate set: the inventory lists every host the registry names
  (Claude Code, Codex, OpenCode); the gate set holds the hosts under native
  qualification gates (Claude and Codex) (REQ-006, OD-4).
- Held-out set, attempt, repetition and retry: as defined in REQ-008.
- CLI-only fallback: the harness CLI through `launch` as the only path when the skill is
  not shipped (REQ-008, REQ-010).

Values named in this spec:

- Skill frontmatter fields (closed, REQ-002): `name`, `description`, `compatibility`,
  `metadata`.
- OpenCode registry row (REQ-006): `observedBuild: null`, `qualification: "unqualified"`.
- Profile format (OD-4): `braid-harness-profile` `v0.2`; `v0.1` read as legacy.
- Prompt kinds (REQ-008): relevant, forbidden-effect.
- Attempt failure signature named in REQ-008: `no-evidence`.
- Stable codes named: the refusals `unsupported-host` and `unknown-host` (REQ-006);
  the result code `opencode-acceptance-unobserved` (REQ-007); `host-build-drift` is the code a
  pre-change record must not raise (REQ-006).
- Telemetry flag and counters: `--telemetry local`; `harness-*` operation counts
  (REQ-009).
- Release outcomes (REQ-010): "ship", "not shipped".

## Non-goals

Promotion pointers in the skill output (SPEC-085 may add them); any claim that the
harness is useful (SPEC-049 T014 was inconclusive; D7 keeps it experimental).

## Risks

- Risk: host models can ignore the skill or run `prepare` by hand, as they can today.
  The CLI's own limits stay the guard and the skill adds no authority (see REQ-004
  and REQ-008).
- Risk: adding a host to shared tuples can silently change gate semantics (REQ-006,
  OD-4).
- Risk: OpenCode schema drift. The plural keys came from vendor docs read once
  (2026-11-22), T007 observed that 2.1.4 reads both shapes, and the plugin package name
  is inconsistent between sources (REQ-007).
- Risk: one model per host and a small prompt set make validity results descriptive
  (REQ-008).
- Risk: a Codex review is independent model review, not human review or approval
  (REQ-010).

## Assumptions

- Assumption: the plugin `launch` keeps exposing the harness CLI read commands as
  merged (SPEC-049 T009) (REQ-003, T003).
- Assumption: the `setup` skill keeps defining how the installed launch path is
  resolved (REQ-003).
- Assumption: host models have shell access to run the launch (REQ-003, REQ-008).
- Assumption: the T007 observation (OpenCode 2.1.4 on one macOS machine) represents
  the OpenCode build users run; another build can read other shapes (REQ-007, T007).

## Exit criteria

Verification is complete when each of procedure_001 to procedure_010 in the
[validation plan](validation-plan.md) has obtained evidence, passing or failing,
recorded against its task in [tasks.md](tasks.md), and the release decision record
(T012) and the publication record (T015) exist. A failing REQ-008 or a "not shipped"
decision completes verification as a negative result (REQ-008, REQ-010).

## Dependencies

ADR 0044 (this spec's decision), ADR 0043 (Rejected), ADR 0037 (OpenCode plugin),
SPEC-049 (T009 views, D7), SPEC-050 (D3, D7), SPEC-054 (skill naming), SPEC-068
(OpenCode integration), SPEC-047 (telemetry, #1405), SPEC-077 (design history).
Consumed by SPEC-081 (Pi and ThinkRail) and SPEC-085 (pointer display).

## References

[Harnessing benchmark](../../docs/strategy/HARNESSING_BENCHMARK.md);
[ADR 0044](../../docs/adr/0044-harness-portability-tiers-skill-surface.md);
[ADR 0043](../../docs/adr/0043-harness-mcp-readonly-surface.md);
[CONSTITUTION.md](../../CONSTITUTION.md); [GOVERNANCE.md](../../GOVERNANCE.md);
[HARNESSING.md](../../docs/tooling/HARNESSING.md);
[NATIVE_PLUGINS.md](../../docs/tooling/NATIVE_PLUGINS.md);
[Agent Skills](https://agentskills.io);
[AAIF porting guide](https://aaif.io/blog/how-to-move-a-skill-from-one-coding-agent-to-another);
[OpenCode config](https://opencode.ai/docs/config).
