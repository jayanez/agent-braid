# Implementation plan: SPEC-087 Host registry

## Technical context and scope

Engineering change, behavior preserving. One new module, `agent_braid/host_registry.py`,
replaces the literal host lists listed below. Python 3.12, standard library only. No
host, capability, input spelling for an unsupported host, stored byte or packaged asset
changes. SPEC-088 (Codex in Braid Lightning) and SPEC-081 (Pi and ThinkRail) register
through it later; this plan implements neither.

### Host sites (verified 2026-11-27)

An AST scan of `agent_braid/` and `scripts/` on `develop` at 2a524884 (tuples, lists,
sets and dictionaries with two or more of `codex`, `claude`, `claude-code`, `opencode`
as string constants) finds **63 collections in 34 files**, plus the packaged
`integrations/agent-braid/hosts.json`. 34 collections are product code and are replaced
or pinned by this change; 29 are listed exceptions (below). Line numbers drift; the guard
test (REQ-010) and the scan baseline (T002), not this table, are the lasting check.

**Replaced or pinned (34 collections).** "Order today" is the order in the source.

| # | Site | Today (order today) | Becomes | Task |
|---|---|---|---|---|
| 1 | `integrations/agent-braid/hosts.json` | `codex, claude, opencode` | unchanged; checked against the registry (REQ-008) | T006 |
| 2 | `agent_braid/plugin_cli.py:36` | `--host` choices `codex, claude, opencode` | `plugin-assets` | T006 |
| 3 | `agent_braid/tooling_cli.py:37` | `--host` choices `codex, claude, opencode` | `plugin-assets` | T006 |
| 4 | `agent_braid/tooling_install.py:728` (`_PROFILES`), `:448`, `:1276` | keys `codex, claude, opencode`; branch on `"claude"`; `hosts.json` equality | profile table keyed by `plugin-assets` (key-set test); `:1276` compares the registry's stored spelling | T006 |
| 5 | `scripts/build_native_plugin.py:427` | provenance `codex, claude, opencode` | registry `plugin-assets` stored spelling; bytes unchanged | T006 |
| 6 | `scripts/reproduce_native_plugin.py:155` | provenance equality `codex, claude, opencode` | same registry read | T006 |
| 7 | `agent_braid/tooling_hosts.py:33`, `:315` | set `codex, claude-code`; `"codex" if … else "claude"` | `tooling-measurement`; conversion is `spelling(host, "host-events")` | T005 |
| 8 | `agent_braid/tooling_evaluation.py:35` | `HOSTS` `codex, claude-code` | `tooling-measurement` | T005 |
| 9 | `agent_braid/tooling_human_audit.py:29` | `HOSTS` `codex, claude-code` | `tooling-measurement` | T005 |
| 10 | `agent_braid/tooling_subscription_estimate.py:28` | frozenset `codex, claude-code` | `tooling-measurement` | T005 |
| 11 | `agent_braid/tooling_subscription.py:23` | `_AUTH` keys `codex, claude-code` | table stays; key set equals `tooling-measurement` | T005 |
| 12 | `agent_braid/tooling_interface_observer.py:28` | `_ORIGINS` keys `codex, claude-code` | table stays; key set equals `tooling-measurement` | T005 |
| 13 | `agent_braid/tooling_model_identity.py:93`, `:94`, `:110` | provider, authentication and domain tables keyed `codex, claude-code` | tables stay; key sets equal `tooling-measurement` | T005 |
| 14 | `agent_braid/tooling_host_events.py:16`, `:183` | `Literal` and membership test `codex, claude` | `host-events` with stored spelling | T005 |
| 15 | `agent_braid/tooling_incremental_usage.py:25`, `:182` | `Literal` and membership test `claude, codex` (membership only, order unobservable) | `host-events` with stored spelling | T005 |
| 16 | `agent_braid/lightning_config.py:25` | `HOSTS` `claude-code, opencode` | `lightning-run` | T005 |
| 17 | `agent_braid/lightning_schema.py:37` | `HOSTS` `claude-code, opencode` | `lightning-run` | T005 |
| 18 | `agent_braid/lightning_export.py:863` | membership test `claude-code, opencode` | `lightning-run` | T005 |
| 19 | `agent_braid/lightning_runner.py:54`, `:319`, `:323` | credential, fake-binary and binary tables keyed `claude-code, opencode` | tables stay; key sets equal `lightning-run` | T005 |
| 20 | `agent_braid/lightning_hosts.py:40`, `:383` | `META_TOOLS` and `PARSERS` keyed `claude-code, codex, opencode` | tables stay; key sets equal `lightning-tool-classes` | T005 |
| 21 | `agent_braid/harness_hosts.py:36`, `:42` | `GATED_HOSTS` `claude, codex`; `_ITEMS` labels | `harness-gated` with stored spelling; `_ITEMS` labels stay | T006 |
| 22 | `agent_braid/harness_components.py:79`, `:80` | `HOSTS` `claude, codex, opencode`; `GATED_HOSTS` `claude, codex` | `harness-inventory`, `harness-gated` with stored spelling | T006 |
| 23 | `agent_braid/harness_components.py:95` | `HOST_SUPPORT` keys `claude, codex, opencode` (rows with `observedBuild`, `qualification`) | rows stay unchanged; key set equals `harness-inventory` | T006 |
| 24 | `agent_braid/harness_hooks.py:70` | `_MODELED` keys `claude, codex` | table stays; key set equals `harness-gated` | T006 |
| 25 | `agent_braid/view_cli.py:49` | `HOSTS` `claude, codex` | `viewer-hosts` with stored spelling | T006 |
| 26 | `agent_braid/view_loom.py:53` | `HOSTS` `braid, claude, codex, other` | `("braid", *viewer-hosts, "other")`; `braid` and `other` stay viewer labels (REQ-015) | T006 |

Rows 2 to 26 account for 34 collections (rows with several lines count each line).

**Listed exceptions (29 collections in 10 files).** The guard test (REQ-010) allows
exactly these files; the owner confirmed each reason at T001 on 2026-11-27 (OD-5).

| Files | Collections | Reason |
|---|---|---|
| `scripts/spec069_native_runs.py`, `scripts/spec069_scoring.py`, `scripts/spec069_capture_t005_evidence.py`, `scripts/spec069_host_probe.py` | 18 | SPEC-069 and SPEC-072 measurement drivers: host-keyed driver tables and `REQUIRED_HOSTS` tied to recorded held-out evidence. SPEC-088 owns the Codex amendment of `REQUIRED_HOSTS`, so it migrates what it touches. |
| `scripts/run_m45_skills_acceptance.py` | 2 | Closed M4.5 acceptance checklist producer; its output is bound to recorded receipts. |
| `scripts/spec066_t030_receipt.py` | 1 | Receipt field names (`claudeCode`, `codex`, `opencode`), not a host collection. |
| `scripts/spec_kit.py`, `scripts/test_spec_kit_integration.py`, `scripts/validate_spec_kit.py`, `scripts/validate_m0_closure.py` | 8 | Spec Kit agent integrations (`codex`, `claude` assistants of the Spec Kit tooling), not Agent Braid hosts. |

Not hosts, kept where they are: the viewer labels `braid` and `other`, the harness
qualification rows (`observedBuild`, `qualification`, REQ-013), and the per-host
credentials, binaries, authentication labels, origins, parsers, tool-name and event
tables (REQ-009).

### Membership table (recorded behavior, REQ-006)

A capability is an ordered tuple of canonical identifiers. Its order is the order its
observable sites have today; sites that only test membership (rows 14, 15, 18) do not
constrain order. T002 generates this table from the scan and fails if a site's observable
order differs.

| Capability | Members, in order | Stored spelling | Sites |
|---|---|---|---|
| `plugin-assets` | `codex`, `claude-code`, `opencode` | `codex`, `claude`, `opencode` | 1 to 6 |
| `tooling-measurement` | `codex`, `claude-code` | `codex`, `claude-code` | 7 to 13 |
| `host-events` | `codex`, `claude-code` | `codex`, `claude` | 14, 15 |
| `lightning-run` | `claude-code`, `opencode` | `claude-code`, `opencode` | 16 to 19 |
| `lightning-tool-classes` | `claude-code`, `codex`, `opencode` | `claude-code`, `codex`, `opencode` | 20 |
| `harness-gated` | `claude-code`, `codex` | `claude`, `codex` | 21, 22, 24 |
| `harness-inventory` | `claude-code`, `codex`, `opencode` | `claude`, `codex`, `opencode` | 22, 23 |
| `viewer-hosts` | `claude-code`, `codex` | `claude`, `codex` | 25, 26 |

The proposed capability names are descriptive; T001 may rename them before code.

### Stored spelling by surface (REQ-005)

Surfaces: `plugin-assets` (`hosts.json`, the plugin and tooling CLIs, installer profiles
and receipts, provenance) writes `claude`; `harness` writes `claude`; `viewer` writes
`claude`; `host-events` writes `claude`; `lightning` writes `claude-code`; `tooling`
(measurement) writes `claude-code`. `codex` and `opencode` have one spelling everywhere.

## Constitution check before research

| Article | Obligation | How the plan meets it |
|---|---|---|
| 0 | No claim beyond evidence | Equality with recorded membership proves preservation at one commit, not that memberships are right (spec, limits) |
| 5, 14 | Effects explicit, evidence not verdicts | The registry has no effect and no verdict; a capability is not qualification (REQ-014) |
| 13 | Evidence before claims | Before and after differential records (T002, T010) |
| 19 | Real, measurable problem | 63 loose collections (34 in product code); a missed list fails silently (spec, purpose) |
| 20 | Analysis and execution separate | No execution authority; `executionAuthorization` stays `false` (REQ-014) |

No MUST conflict found.

## Research, assumptions and alternatives

- **Registry as a Python module (chosen).** Capability queries are code, the consumers
  are Python and the package already ships `agent_braid`. Alternative: a JSON data file
  read at import. Rejected: adds file reads to import, which REQ-011 forbids, and a
  second place to keep in sync with `hosts.json`.
- **Regenerate `hosts.json` from the registry.** Rejected by OD-1: the file is a packaged
  asset with byte-bound provenance; the registry is checked against it instead.
- **Registry holds credentials, binaries, auth labels, tool names.** Rejected by OD-3:
  it would couple the registry to Lightning, subscription and security details.
- **Convention only.** Rejected by OD-4: loose lists are what this change removes.
- **Write `claude-code` everywhere.** Rejected by OD-2 and the 2026-11-27 owner decision:
  it breaks frozen formats such as `spec048-founder-review-v1`.
- Assumption: `scripts/` and the installed plugin runtime can import
  `agent_braid.host_registry` (`build_native_plugin.py` already imports from
  `agent_braid`; T003 confirms for each script).

## Design and compatibility

- **Module.** `agent_braid/host_registry.py`: a frozen `Host` record (`id`, `aliases`,
  `spellings` by surface, `capabilities`), a constant tuple of the three hosts, and pure
  functions `normalize(value)` (alias or canonical to canonical, else `None`),
  `hosts_with(capability)` (canonical identifiers),
  `spelling(host, surface)` and `from_spelling(surface, value)`. Each capability is an
  ordered tuple of canonical identifiers fixed in the module, so `hosts_with` returns the
  order the observable sites have today, not the host record order. Surfaces and
  capabilities are closed string constants. Unknown surface, capability or host raises
  `ValueError`; consumers keep their own refusal text.
- **Consumers.** Each site reads a query at import or call time instead of declaring a
  list. Input paths call `normalize` first; stored and output paths call `spelling`.
  Existing refusal codes, messages and JSON shapes stay.
- **Feature-owned tables.** Dictionaries keyed by host stay in place (`META_TOOLS`,
  `PARSERS`, `HOST_SUPPORT`, `_MODELED`, `_AUTH`, `_ORIGINS`, the model-identity and
  Lightning runner tables, `_PROFILES`), keyed by canonical identifier where they are not
  already, or by the surface's stored spelling where a frozen format requires it; a test
  compares each key set with its query.
- **Guard.** The scan of T002 (AST walk of `agent_braid/` and `scripts/` for tuples,
  lists, sets and dictionaries with two or more host identifiers or the alias) is one
  module reused by the baseline recorder and the guard test, outside `host_registry.py`
  and the ten exception files above.
- **Argparse text.** `--host` options normalize through the registry. Usage, help and
  invalid-choice text may list `claude-code` in addition; exit status and the absence of
  other output stay (REQ-004, REQ-005).
- **Rollback.** Revert the code PR; no data changed, so nothing to restore.

## Validation strategy

- Differential record first (T002): generate today's membership, order and stored
  spellings from the AST scan, and record the outputs of the fixture commands, from
  `develop` at 2a524884.
- Tests per requirement as in [tasks.md](tasks.md), each with a mutation control: add a
  host, drop a host, change a stored spelling, edit `hosts.json`, add a loose list.
- Existing suites for Lightning, harness, viewer, tooling install, host events and
  native plugin reproduction run unchanged.
- Drafting: `python3 scripts/validate_spec_kit.py` in a fresh clone (the local object
  store fails the portable-root gate), `python3 scripts/validate_repository.py`,
  `python3 scripts/sync_github_tracking.py source`. Code phase: targeted tests, then
  `python3 scripts/validate_change.py --base develop --profile quick`; the CI `validate`
  aggregate is the `pr`-profile evidence. A passing profile is not approval.

## Constitution check after design

No MUST conflict. The one deliberate difference from earlier host code: stored spellings
differ by surface on purpose, to keep frozen data valid (REQ-005, REQ-012).

## Human review and unresolved decisions

OD-1 to OD-4 were answered by the owner on 2026-11-27 (see the spec). OD-5, the exception
list and the fake-host test, and the capability names were approved by the owner at T001
on 2026-11-27 ([record](evidence/owner-decisions-20261127.md)).

## Affected files for the later code phase (named, not edited)

- New: `agent_braid/host_registry.py`, `tests/test_host_registry.py`,
  `tests/test_host_registry_guard.py`.
- New: `scripts/host_scan.py` (the AST scan shared by the baseline and the guard).
- Changed: sites 2 to 26 of the table above.
- Docs: `docs/tooling/HOSTS.md` (how a host is added), `AGENTS.md` or the contributor
  guide line that points to it.
- Unchanged by rule: `integrations/agent-braid/hosts.json`, frozen records and
  evidence, `CONSTITUTION.md`, SPEC-080 and SPEC-081.
