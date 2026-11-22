# Implementation plan: SPEC-081 Pi and ThinkRail host integration

## Approach

Observe first, then design, then build, as SPEC-068 did for OpenCode.

1. **Observe.** A one-command capture script, modelled on the SPEC-048 Codex capture
   (#1421, `scripts/har_codex_capture.py`), runs Pi in a disposable profile (a
   temporary configuration directory, or a temporary `HOME` if Pi offers no
   override). It records the matrix rows of REQ-002 and writes a redacted shape
   summary with SHA-256 hashes. Raw output stays under
   `~/agent-braid-private/pi-capture/<stamp>/` (mode 0700). A `--dry-run` mode checks
   the binary, version and sign-in without sending a prompt. ThinkRail is a GUI; rows
   the script cannot drive get a short owner runbook or stay `unobserved`.
2. **Design.** Amend the spec from the observed rows (SC-003). Draft the Pi surface
   ADR (OD-6) and a surface contract under `contracts/`.
3. **Build.** Add the Pi package target to the shared `plugin-dist` artifact, the
   installer profile, the doctor module and the host lists. Pi enters the harness
   host registry as unqualified, offline only.
4. **Observe the candidate and release.** Run the native observation runbook on the
   built candidate in disposable profiles; release only after alpha.10 and an
   explicit owner decision (OD-7).

## Constitutional check

| Article | Obligation | How the plan meets it |
|---|---|---|
| 0 | No claim beyond evidence | Vendor facts stay unverified until REQ-002; a negative row is a valid result |
| 5, 15 | Effects are explicit | Installer writes only receipt-owned entries; doctor is read-only; hidden host writes (Gentle AI) surface as findings |
| 13, 14 | Evidence, not verdicts | Capture rows are observations pinned to a binary hash and version, with limits, not acceptance |
| 19 | Real problem | Owner wants the plugin wherever Pi or ThinkRail runs (benchmark, Pi row) |
| 20 | Analysis and execution separate | No grant from host approvals; `executionAuthorization` false (REQ-007) |
| 23, 24 | Semantics before production | Observation and ADR precede code; release gated on REQ-008 |

Privacy follows [GOVERNANCE.md](../../GOVERNANCE.md) and SPEC-047 consent rules: raw
session JSONL stays private and only redacted shapes are committed.

No MUST conflict found. No SHOULD deviation recorded.

## Affected files in the later code phase (named, not edited)

- `scripts/pi_host_capture.py` and `tests/test_pi_host_capture.py` (new; fake binary
  in tests, as #1421).
- `scripts/build_native_plugin.py`: Pi package target (`package.json` with `skills`,
  and `extensions` only under OD-4), check of packaged names and byte identity.
- `agent_braid/tooling_install.py`: a `pi` entry in `_PROFILES` and its
  configuration reader, receipt-owned edits of Pi's `mcp.json` (REQ-004, OD-5).
- `agent_braid/tooling_cli.py`, `agent_braid/plugin_cli.py`: `--host` choices.
- `agent_braid/plugin_pi.py` (new): read-only diagnosis, as `plugin_opencode.py`.
- `install.sh` and `integrations/agent-braid/hosts.json`: host selection.
- `agent_braid/harness_hosts.py`, `agent_braid/harness_components.py`
  (`HOSTS`, `HOST_SUPPORT`) and `agent_braid/harness_lifecycle.py`: Pi as
  unqualified, offline only. Coordinated with SPEC-080, which adds OpenCode there.
- `agent_braid/tooling_hosts.py` is the session dispatch adapter, not a host list.
  It stays unchanged because native Pi sessions are out of scope.
- `docs/tooling/NATIVE_PLUGINS.md`, `docs/tooling/INSTALL.md`,
  `docs/tooling/HOSTS.md`, README quick start: Pi and ThinkRail rows and the
  no-permission-layer limit.
- Tests: plugin build, installer profile, doctor, host-list consistency.

## Phases

| Phase | Tasks | Gate to the next phase |
|---|---|---|
| P0 review | T001, T002 | Owner record; Codex review triaged |
| P1 observation | T003, T004 | Capture committed; spec amended where contradicted |
| P2 design | T005 | ADR and surface contract reviewed by the owner |
| P3 build | T006 to T010 | Tests pass with mutation controls; `quick` green |
| P4 candidate | T011, T012 | Native observation without contradiction; owner release decision |

## Validation profile

- This PR (documentation only): `python3 -m scripts.validate_spec_kit` and
  `python3 scripts/validate_change.py --base develop --profile quick`. The new
  assurance record is sensitive and may escalate the quick profile; that is
  expected.
- Code phase: targeted tests for the touched modules, then `quick`; the CI
  `validate` aggregate on the PR head is the `pr` evidence. Plugin build and
  installer changes are supply-chain inputs; follow the sensitive rules of
  `docs/development/VALIDATION_PROFILES.md`.
- Capture and native observation are owner-run evidence, never implied by a
  passing profile.

## Rollback

- Documentation phase: revert the PR.
- Code phase: the Pi target is additive. Rollback is reinstalling the previous
  plugin release; `agent-braid tooling uninstall --host pi` removes receipt-owned
  entries only. Other hosts' bytes are unchanged (SC-004), so they need no rollback.
