# Implementation plan: SPEC-088 Codex as a Braid Lightning host

## Technical context and scope

Engineering change; additive for Codex, behavior preserving for `claude-code` and
`opencode`. Python 3.12, standard library only. It uses the SPEC-087 host registry
(`agent_braid/host_registry.py`, not yet implemented at 65f101ba) and edits the
Lightning modules that today list hosts. It changes no recorded evidence, no SPEC-069
driver and no required-host verdict. Capability names below are SPEC-087's proposals;
SPEC-087 T001 may rename them, and this plan follows the names merged there.

### Lightning host sites (verified 2026-11-27)

An AST scan of `agent_braid/` and `scripts/` on `develop` at 65f101ba finds every string
constant `claude`, `claude-code`, `codex` or `opencode` in a module that mentions
Lightning. SPEC-087's scan counts collections of two or more hosts; this scan also
counts single-host comparisons, which it does not see. Line numbers drift; the T002
baseline and the guard test of SPEC-087, not this table, are the lasting check.

**Edited by this change.** "Order today" is the order in the source.

| # | Site | Today | Becomes | Task |
|---|---|---|---|---|
| 1 | `agent_braid/lightning_config.py:25` `HOSTS` | `claude-code, opencode` (feeds rows 2 to 4) | `lightning-run` | T004, T005 |
| 2 | `lightning_config.py:40` default `rollout.hosts` | `list(HOSTS)` | fixed default `['claude-code', 'opencode']` (REQ-005) | T005 |
| 3 | `lightning_config.py:54` `optimizer.host` enum | `HOSTS`, default `claude-code` | `lightning-optimizer` (REQ-004) | T005 |
| 4 | `lightning_cli.py:70` `--optimizer-host` choices | `config.HOSTS` | `lightning-optimizer` | T005 |
| 5 | `lightning_schema.py:37` `HOSTS` (rollout, model identity, `attempt_start`) | `claude-code, opencode` | `lightning-run` | T005 |
| 6 | `lightning_export.py:863` terms record `host` | `claude-code, opencode` | `lightning-run` | T005 |
| 7 | `lightning_runner.py:54` `CREDENTIALS` | keys `claude-code, opencode` | table stays; key set equals `lightning-run`; `codex` value per T003 | T006 |
| 8 | `lightning_runner.py:319` `_fake_binary` table | keys `claude-code, opencode` | table stays; key set equals `lightning-run`; `codex` fixture | T006 |
| 9 | `lightning_runner.py:323` `_host_binary` table | keys `claude-code, opencode`; OpenCode fallback path | table stays; key set equals `lightning-run`; `codex` binary per T003 | T006 |
| 10 | `lightning_runner.py:266-272` `key_source_verdict` | `claude-code` in `{oauth, none}`, `opencode` = `oauth` | per-host accepted sources table keyed by `lightning-run`; `codex` accepts only T003's observed value; none until then | T006 |
| 11 | `lightning_runner.py:703-706` declared limit on `route-unverified` | `host_name == 'opencode'` | table keyed by `lightning-run`: `opencode` and `codex` | T006 |
| 12 | `lightning_hosts.py:40` `META_TOOLS`, `:383` `PARSERS`, `tool_class` `:389-393` | keys `claude-code, codex, opencode` | unchanged; key set equals `lightning-tool-classes`; `codex` entries verified (REQ-009) | T007 |
| 13 | `tests/fixtures/lightning-fake-hosts/` | `claude`, `opencode` | add `codex` | T006 |

**Read, not edited (kept as they are).**

| Site | Today | Why it stays |
|---|---|---|
| `lightning_runner.py:142` `SandboxedHost` refusal | any host but `claude-code` is `route-unverified` | the optimizer stays on `claude-code` (REQ-004, OD-2) |
| `lightning_arm.py:188`, `lightning_cli.py:308,313` `models={'claude-code': ...}` | `--model` names the `claude-code` model | optimizer and rollout model flag are Claude-only; a Codex model flag is not added (Codex runs on its host default; model identity per T003) |
| `lightning_evaluation.py:34` `REQUIRED_HOSTS` | `("claude-code",)` | REQ-011, OD-1; SPEC-087's scan sees no collection of two |
| `scripts/spec071_real_baseline.py`, `spec072_development_arms.py`, `spec073_owner_promotion.py` | `claude-code` literals | closed SPEC-071 to SPEC-073 evidence drivers (REQ-016) |
| `scripts/spec069_native_runs.py`, `spec069_scoring.py`, `spec069_host_probe.py`, `spec069_capture_t005_evidence.py` | host tables already include `codex` | SPEC-087 exception files; this change consumes the driver unchanged and migrates nothing it does not touch (REQ-016) |
| `agent_braid/plugin_cli.py`, `scripts/build_native_plugin.py` | plugin asset hosts | not Lightning; SPEC-087 sites 2 to 6 |

The consent check at `lightning_cli.py:300` and `lightning_adapter.py:28` carries no host
literal, so no consent edit is planned (REQ-012; T002 confirms).

### Membership table after this change (REQ-002, REQ-005)

| Capability | Today | After | Order rationale |
|---|---|---|---|
| `lightning-run` | `claude-code`, `opencode` | `claude-code`, `opencode`, `codex` | `codex` appended, so the prefix equals today's order and every order-observing site (table iteration, serialized lists, argparse choices) keeps its current prefix |
| `lightning-optimizer` (new) | none (the same tuple served both) | `claude-code` | `optimizer.host` and `--optimizer-host` only |
| `lightning-tool-classes` | `claude-code`, `codex`, `opencode` | unchanged | already includes `codex` |
| `tooling-measurement`, `host-events`, `plugin-assets`, `harness-*`, `viewer-hosts` | per SPEC-087 | unchanged | not touched |

Registry edit: the code PR edits SPEC-087's capability data (adds `codex` to
`lightning-run`, adds `lightning-optimizer`) and updates its recorded membership table,
the registry test fixtures and the SPEC-087 guard's expectations. SPEC-087 REQ-007 binds
SPEC-087's own change set to today's membership; this change is the next change and
follows SPEC-087's extension path (its REQ-017). A SPEC-087 test that fails on adding a
capability without a table change is satisfied by the table update in the same PR.

### Fixtures and recorded behavior

T002 records, from `develop` before any Lightning edit and after SPEC-087's code:

- the output bytes of `lightning init` preview (default and with `--optimizer-host`),
  `run --dry-run`, `run --fake-hosts`, `status`, `report`, the config and schema refusals,
  the export terms refusals and the default-config digest;
- the SHA-256 of every committed Lightning fixture and record;
- the host-site scan of this table, regenerated, failing on any site that is neither in
  the table nor in a stated exception.

## Constitution check before research

| Article | Obligation | How the plan meets it |
|---|---|---|
| 0 | No claim beyond evidence | No Codex result is claimed; route and parser are verified by observation first (REQ-007, REQ-009, REQ-017) |
| 5, 14 | Effects explicit, evidence not verdicts | A Codex run is an explicit, owner-authorized task; the report is not a verdict (REQ-011, REQ-015) |
| 13 | Evidence before claims | Differential record before the change (T002); Codex observation before use (T003) |
| 19 | Real, measurable problem | Codex is refused at configuration time and blocks #1700; the shared tuple would otherwise make it a default and an optimizer host |
| 20 | Analysis and execution separate | Fake hosts only in the change; the real run is T011 with the owner's yes |

No MUST conflict found.

## Research, assumptions and alternatives

- **Add `codex` to the shared tuple only (rejected).** One edit, but it makes Codex a
  default `rollout.hosts` entry (default `list(HOSTS)`), changes the default
  configuration digest for everyone, and makes `optimizer.host: codex` validate and fail
  late. Chosen: a separate `lightning-optimizer` capability and a fixed default
  (REQ-004, REQ-005).
- **Make Codex a required host now (rejected by OD-1).** It would change the closed
  SPEC-072 and SPEC-073 criteria with no Codex measurement in Lightning.
- **Accept the profile's ChatGPT sign-in as route proof (rejected by OD-3).** A looser
  bar than the one Claude Code meets and not observed in the stream.
- **New schema version (rejected by OD-4).** Collides with the `v0.2` name SPEC-076
  reserves and changes readers, store and export.
- **Registry holds credentials, binaries, parsers (rejected, SPEC-087 REQ-009).** They
  stay in `lightning_runner.py` and `lightning_hosts.py`, pinned by key-set tests.
- **Reuse the SPEC-069 driver (chosen).** `spec069_native_runs.py` already launches Codex
  (`prompt_argv`, `install_plugin`, `build_host_env`, `AUTH_*`, `KEY_SPECS`); the Lightning
  runner calls it for the other hosts. Assumption: it works for Codex inside the
  Lightning profile; T003 and T006 test it with the fake host and, if needed, a probe.
- **Credential carrier for Codex is not decided here.** The runner reads a credential
  from an environment variable for `claude-code` (`CLAUDE_CODE_OAUTH_TOKEN`) and none
  for `opencode`. The driver supports a dedicated sign-in directory for Codex
  (`CODEX_HOME`, `auth.json`) that the driver points at and never reads. T003 observes
  which carrier and which reported source exist; the owner reviews it before the
  `CREDENTIALS` and `key_source_verdict` entries are written (OD-3, OD-6).

## Design and compatibility

- **Registry.** Add `codex` to `lightning-run` and a `lightning-optimizer` capability;
  consumers query them. Order is append-only so existing observable orders keep their
  prefix.
- **Config.** `rollout.hosts` options come from `lightning-run`; its default is the
  literal pair `['claude-code', 'opencode']`, kept as a constant in the config module and
  pinned to a subset of `lightning-run` by a test, so a later host added to the
  capability does not silently join the default. `optimizer.host` options and the CLI
  choices come from `lightning-optimizer`.
- **Schema and export.** Host enums read `lightning-run`; version strings stay.
- **Runner tables.** `CREDENTIALS`, the fake-binary and binary tables, the accepted
  key-source table and the declared-limit table are keyed by `lightning-run` members and
  stay in `lightning_runner.py`; the OpenCode special cases become table lookups with
  the same results for `opencode`. `codex` entries are written from T003's evidence; until
  then `codex` accepts no source and ends as a declared limit.
- **Held-out guard.** `plan()` and `run()` refuse a `codex` host for a prompt set in
  `HELDOUT` or `TEST_SETS` before launch (REQ-014, OD-5).
- **Fake host.** `tests/fixtures/lightning-fake-hosts/codex` mirrors the existing fixtures
  and reuses the SPEC-069 fake Codex behavior; it reports no model credential.
- **Docs.** `docs/tooling/LIGHTNING.md` states that Codex is a rollout host, that it is
  non-binding, that its route is `route-unverified` until evidence exists, that the
  optimizer stays on Claude Code, and the held-out guard; it claims no result (REQ-017).
- **Rollback.** Revert the code PR; no data changed. A Codex record already written would
  stop being readable by a reader without `codex`.

## Validation strategy

- Differential record first (T002), repeated after (T010): identical bytes and sets for
  `claude-code` and `opencode`, apart from accepted-host text in refusals.
- One test per requirement as in [tasks.md](tasks.md), each with a mutation control:
  drop `codex` from a table, add it to `lightning-optimizer`, add it to
  `REQUIRED_HOSTS`, derive the default from the whole capability, accept a Codex source
  that was not observed, run Codex on a held-out set.
- `--fake-hosts` pipeline test with `claude-code`, `opencode` and `codex` (REQ-010).
- Codex stream verification (T003, T007) on recorded streams, naming the Codex build.
- Existing Lightning, SPEC-069 driver and SPEC-087 suites run unchanged.
- Drafting: `python3 scripts/validate_spec_kit.py` in a fresh clone (the local object
  store fails the portable-root gate), `python3 scripts/validate_repository.py`,
  `python3 scripts/sync_github_tracking.py source`. Code phase: targeted tests, then
  `python3 scripts/validate_change.py --base develop --profile quick`; the CI `validate`
  aggregate is the `pr`-profile evidence. A passing profile is not approval.

## Constitution check after design

No MUST conflict. The deliberate differences from a one-line change: a second capability
for the optimizer and a fixed default for `rollout.hosts`, to keep every existing
configuration and output unchanged.

## Human review and unresolved decisions

OD-1 to OD-4 were answered by the owner on 2026-11-27 (see the spec). OD-5 (held-out
guard) is open and is reviewed at T001. OD-6 (the real run, its credential carrier and
Codex build) is decided at T003 and T011 on observed evidence.

### Proposed amendments to SPEC-087 (not made; SPEC-087 is merged)

1. Extend T002's scan to single-host comparisons and branches (for example
   `host == 'opencode'`), which the collection scan does not see; at least
   `lightning_runner.py:703` is such a site.
2. Record the `lightning-optimizer` capability, or allow a capability to be added by a
   later spec through REQ-017.
3. Name the SPEC-069 to SPEC-073 scripts as consumers that SPEC-088 reads unchanged, so
   the exception list stays valid.

## Affected files for the later code phase (named, not edited)

- Changed: `agent_braid/host_registry.py` (capability data), `agent_braid/lightning_config.py`,
  `agent_braid/lightning_cli.py`, `agent_braid/lightning_schema.py`,
  `agent_braid/lightning_export.py`, `agent_braid/lightning_runner.py`,
  `agent_braid/lightning_hosts.py` (verification only unless T003 requires a fix),
  their tests, `docs/tooling/LIGHTNING.md`.
- New: `tests/fixtures/lightning-fake-hosts/codex`, `tests/test_lightning_codex_host.py`,
  evidence under `specs/088-lightning-codex-host/evidence/`.
- Unchanged by rule: SPEC-069 to SPEC-073 scripts and evidence, `REQUIRED_HOSTS`,
  closed specifications, SPEC-087, `CONSTITUTION.md`.
