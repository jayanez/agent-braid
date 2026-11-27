# Implementation plan: SPEC-087 Host registry

## Technical context and scope

Engineering change, behavior preserving. One new module, `agent_braid/host_registry.py`,
replaces the literal host lists listed below. Python 3.12, standard library only. No
host, capability, input spelling for an unsupported host, stored byte or packaged asset
changes. SPEC-088 (Codex in Braid Lightning) and SPEC-081 (Pi and ThinkRail) register
through it later; this plan implements neither.

### Host sites (verified 2026-11-27)

Verified by reading each site on `develop` at 2a524884. Line numbers drift; the guard
test (REQ-010), not this table, is the lasting check.

| # | Site | Today | Becomes |
|---|---|---|---|
| 1 | `integrations/agent-braid/hosts.json` | `["codex","claude","opencode"]` | unchanged; checked against the registry (REQ-008) |
| 2 | `agent_braid/plugin_cli.py:36` | `--host` choices `('codex','claude','opencode')` | `plugin-assets` query; `claude` and `claude-code` accepted |
| 3 | `agent_braid/tooling_hosts.py:33`, `:315` | `_SUPPORTED_HOSTS={"codex","claude-code"}`; `"codex" if … else "claude"` conversion | `tooling-measurement` query; conversion becomes `spelling(host, "host-events")` |
| 4 | `agent_braid/tooling_host_events.py:16` | `Host=Literal["codex","claude"]` | `host-events` query with stored spelling; the type stays a closed literal derived from it |
| 5 | `agent_braid/lightning_config.py:25` | `HOSTS=('claude-code','opencode')` | `lightning-run` query |
| 6 | `agent_braid/lightning_runner.py:54`, `:319`, `:323` | `CREDENTIALS`, `_fake_binary` and `_host_binary` dictionaries keyed by host | feature-owned tables, key sets equal `lightning-run` (REQ-009) |
| 7 | `agent_braid/lightning_hosts.py:40` | `META_TOOLS` keyed `claude-code`, `codex`, `opencode` | feature-owned table, key set equals `lightning-tool-classes` |
| 8 | `agent_braid/harness_hosts.py:36`, `:45` | `GATED_HOSTS=("claude","codex")`; `_ITEMS` labels to `claude`, `codex` | `harness-gated` query with stored spelling; `_ITEMS` labels stay |
| 9 | `agent_braid/harness_components.py:79` (docstring `:41`) | `HOSTS=("claude","codex","opencode")` | `harness-inventory` query with stored spelling |
| 10 | `agent_braid/view_cli.py:49` | `HOSTS=("claude","codex")` | `viewer-hosts` query with stored spelling |
| 11 | `agent_braid/view_loom.py:53` | `HOSTS=("braid","claude","codex","other")` | `("braid", *viewer-hosts, "other")`; `braid` and `other` stay viewer labels (REQ-015) |
| 12 | `agent_braid/tooling_subscription.py:23` | `_AUTH={"codex":"chatgpt","claude-code":"claude.ai"}` | feature-owned table, key set equals `subscription-auth` |
| 13 | `agent_braid/tooling_install.py:728-745` (`_PROFILES`), `:448`, `:1276` | profile keys `codex`, `claude`, `opencode`; branch on `"claude"`; `hosts.json` equality check | keys and branches from `plugin-assets`; `:1276` compares with the registry's stored spelling |
| 14 | `scripts/build_native_plugin.py:427` | `{'hosts': ['codex','claude','opencode']}` in provenance | read from the registry's `plugin-assets` stored spelling; bytes unchanged |
| 15 | `scripts/reproduce_native_plugin.py:155`, `:204` | provenance equality; loop over `codex`, `claude` | same registry reads |

Not hosts, kept where they are: the viewer labels `braid` and `other` (site 11), the
harness qualification rows (`observedBuild`, `qualification`, REQ-013), the per-host
credentials, binaries, authentication labels and tool-name tables (sites 6, 7, 12;
REQ-009).

### Membership table (recorded behavior, REQ-006)

Hosts are canonical identifiers, listed in registry order. The proposed capability names
are descriptive; T001 may rename them before code.

| Capability | Members | Stored spelling (claude / codex / opencode) | Source sites |
|---|---|---|---|
| `plugin-assets` | `codex`, `claude-code`, `opencode` | `claude` / `codex` / `opencode` | 1, 2, 13, 14, 15 |
| `tooling-measurement` | `codex`, `claude-code` | `claude-code` / `codex` | 3 |
| `subscription-auth` | `codex`, `claude-code` | `claude-code` / `codex` | 12 |
| `host-events` | `codex`, `claude-code` | `claude` / `codex` | 3, 4 |
| `lightning-run` | `claude-code`, `opencode` | `claude-code` / `opencode` | 5, 6 |
| `lightning-tool-classes` | `codex`, `claude-code`, `opencode` | `claude-code` / `codex` / `opencode` | 7 |
| `harness-gated` | `codex`, `claude-code` | `claude` / `codex` | 8 |
| `harness-inventory` | `codex`, `claude-code`, `opencode` | `claude` / `codex` / `opencode` | 9 |
| `viewer-hosts` | `codex`, `claude-code` | `claude` / `codex` | 10, 11 |

Order inside a query follows the registry (`codex`, `claude-code`, `opencode`); a surface
whose current list has another order keeps its order through its stored spelling list
(for example Lightning's `claude-code`, `opencode`), recorded by the differential test
(T002, T010).

### Stored spelling by surface (REQ-005)

Surfaces: `plugin-assets` (`hosts.json`, the plugin CLI, installer profiles and
receipts, provenance) writes `claude`; `harness` writes `claude`; `viewer` writes
`claude`; `host-events` writes `claude`; `lightning` writes `claude-code`; `tooling`
writes `claude-code`. `codex` and `opencode` have one spelling everywhere.

## Constitution check before research

| Article | Obligation | How the plan meets it |
|---|---|---|
| 0 | No claim beyond evidence | Equality with recorded membership proves preservation at one commit, not that memberships are right (spec, limits) |
| 5, 14 | Effects explicit, evidence not verdicts | The registry has no effect and no verdict; a capability is not qualification (REQ-014) |
| 13 | Evidence before claims | Before and after differential records (T002, T010) |
| 19 | Real, measurable problem | Fifteen loose sites; a missed list fails silently (spec, purpose) |
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
  `hosts_with(capability)` (canonical identifiers in registry order),
  `spelling(host, surface)` and `from_spelling(surface, value)`. Surfaces and
  capabilities are closed string constants. Unknown surface, capability or host raises
  `ValueError`; consumers keep their own refusal text.
- **Consumers.** Each site reads a query at import or call time instead of declaring a
  list. Input paths call `normalize` first; stored and output paths call `spelling`.
  Existing refusal codes, messages and JSON shapes stay.
- **Feature-owned tables.** Dictionaries keyed by host stay in place, keyed by canonical
  identifier where they are not already; a test compares each key set with its query.
- **Guard.** A test walks the AST of `agent_braid/` and `scripts/` and reports a tuple,
  list, set, frozenset or dict whose string constants include two or more host
  identifiers or the alias, outside `host_registry.py` and an exception list. Initial
  exceptions are named in T007 (for example `hosts.json` readers' expected-value checks
  and frozen format constants) with a reason each.
- **Rollback.** Revert the code PR; no data changed, so nothing to restore.

## Validation strategy

- Differential record first (T002): export today's membership, per-surface stored
  spellings and the outputs of the fixture commands from `develop` at 2a524884.
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

OD-1 to OD-4 were decided on 2026-11-27 and are recorded in the spec. T001 records the
owner's review of the final text, including the capability names, before code.

## Affected files for the later code phase (named, not edited)

- New: `agent_braid/host_registry.py`, `tests/test_host_registry.py`,
  `tests/test_host_registry_guard.py`.
- Changed: the sites in the table above except `hosts.json`.
- Docs: `docs/tooling/HOSTS.md` (how a host is added), `AGENTS.md` or the contributor
  guide line that points to it.
- Unchanged by rule: `integrations/agent-braid/hosts.json`, frozen records and
  evidence, `CONSTITUTION.md`, SPEC-080 and SPEC-081.
