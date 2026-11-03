# SPEC-068 implementation plan

## Technical context and scope

Python standard library plus the pinned optional `mcp==2.3.0` SDK, the existing
bundled runtime and one dependency-free ES module for OpenCode. Specification
only: nothing below is implemented by this change.

Affected code when implementation is authorized:

| Area | Files | Tasks |
|---|---|---|
| OpenCode entry source | `integrations/agent-braid/plugin/opencode/index.js` (new, tracked) | T003 |
| Native build | `scripts/build_native_plugin.py` (`package.json`, `opencode/`, `check_package_names`, inventory, provenance) | T004 |
| Collision diagnosis | `agent_braid/plugin_cli.py`, new `agent_braid/plugin_opencode.py` (read-only scan) | T005 |
| Shell installer | `install.sh`, `tests/test_plugin_installer.py` | T006 |
| Legacy profile | `agent_braid/tooling_install.py` (host table, JSONC scanner, paths), `integrations/agent-braid/hosts.json`, tooling CLI `--host` choices | T007 |
| Regression | tests for SPEC-046/047/054/060/066 contracts and Codex/Claude artifact diff | T008 |
| Documentation | see REQ-011 list | T009 |

Unaffected: `agent_braid/plugin_mcp.py` tool set and results, `plugin_registry.py`
semantics, telemetry and System One stores, canonical skill sources, Codex and
Claude manifests, `agent_braid/tooling_hosts.py` (harness launch, SPEC-065),
frozen evidence of other specs.

## Constitution check before research

- **Art. 0, 5, 6** (clause zero, authority, evidence): no new authority; host
  permissions are approvals, never grants; every host fact is documented until
  T002 observes it, and the plan names each such fact.
- **Art. 12–13** (boundaries, effects): the OpenCode entry registers only an MCP
  server, skills and commands; no hooks, no network, no writes.
- **Art. 14–16** (inspectable interfaces, vendor neutrality, conservative
  versioning): all behaviour stays in the existing MCP contract; the host binding
  is a thin adapter; additions are versioned and additive, no contract is renamed.
- **Art. 19–20** (practicality, analysis separate from execution): skills and
  commands stay advisory; `execute` still needs an operator grant.
- **Art. 23–25** (claim discipline): no compatibility claim before REQ-012; the
  `unobserved` state is explicit.

GOVERNANCE: public surface additions carry migration notes in release notes and
docs. No MUST conflict found. One SHOULD-level departure is proposed for review:
D12 (OD-9) narrows SC-010's "byte-identical artifacts" to host-read files; the owner accepted it on 2026-11-03. No
constitutional amendment is proposed.

## Research, assumptions and alternatives

See [research.md](research.md) (R1–R7). Assumptions: OpenCode 2.1.x keeps the
documented transforms and discovery order; a dependency-free module loads;
`plugin add` from a Git subdirectory keeps file modes. Each assumption is a T002
row; failure stops the dependent task and returns to the owner.

| Alternative | Outcome |
|---|---|
| TypeScript entry with `@opencode/plugin` | Fallback only if T002 rejects the dependency-free entry (R1) |
| Separate OpenCode plugin directory | Rejected: duplicated runtime, split provenance (R2) |
| npm channel | Requires a new owner decision (D3) |
| Plugin-side automatic MCP reload | Rejected by REQ-005 and ADR 0024 (R5) |
| Rewrite JSONC through a parser | Rejected: loses comments (R6) |
| JSONC library dependency | Rejected for the frozen route (R6) |

## Design and compatibility

1. **Entry module** per [opencode-surface.md](contracts/opencode-surface.md): three
   transforms, `import.meta.url` root, no replacement of existing IDs or a foreign
   `agent-braid` server.
2. **Build.** `assemble` writes `package.json` and copies `opencode/index.js` into
   the shared plugin directory; `check_package_names` also checks
   `package.json.name == "agent-braid"`; `provenance.json` gains
   `hosts: ["codex", "claude", "opencode"]`; inventory lists the new files. The
   SPEC-054 skill substitution is reused unchanged.
3. **Collision diagnosis.** `plugin doctor --host opencode [--project]` scans the
   documented locations (R4); without `--host`, output is unchanged.
4. **Installer.** `install.sh --host opencode` runs
   `opencode plugin add github:jayanez/agent-braid#<tag>::path:plugins/agent-braid`;
   `--host all` adds OpenCode when it is on `PATH`; `both` stays a deprecated
   alias for Codex and Claude only.
5. **Legacy profile** per [opencode-legacy-profile.md](contracts/opencode-legacy-profile.md):
   per-host table in `tooling_install.py`, JSONC scanner used only for `opencode`,
   default server name `agent-braid`, as on the other hosts (D13), with a
   collision warning.
6. **Telemetry, System One, session identifier.** No change; regression tests
   (REQ-009).
7. **Release.** First carrier `0.1.0-alpha.6` (D11). The plugin schema stays
   `agent-braid-plugin/v0.2`; the Python package version follows the release
   decision in T011.
8. **Documentation.** README quick start (OpenCode row), `docs/tooling/NATIVE_PLUGINS.md`,
   `INSTALL.md` (OpenCode legacy profile; route marked frozen fallback),
   `SKILLS.md`, `HOSTS.md`, `PLUGIN_PRIVACY.md`, `docs/tooling/README.md`,
   `docs/development/SPEC_KIT.md` (OpenCode column), SPEC-039 `program.md`
   (additive route note), release notes at publication.

## Validation strategy

Requirement → scenario → procedure → task mapping is in `assurance.json` and
[validation-plan.md](validation-plan.md). Unit procedures use fake `opencode`,
`codex` and `claude` executables and fixture skill trees; the entry module is
checked by a Python test that parses its source for forbidden APIs (network,
filesystem writes, child processes, event subscriptions) and by T010 in a real
host. Repeatable commands are in [quickstart.md](quickstart.md). Run `--profile
quick` after each increment and `--profile pr` once on the stable candidate,
through the clean clone. Negative controls are listed in both contracts.

## Constitution check after design

No effect, grant, execution path, analysis result or evidence boundary changes.
The OpenCode binding is an adapter over the unchanged MCP contract; vendor-specific
behaviour stays in the entry module and the legacy host table. Unobserved host
behaviour is not claimed. D12 and D13 are recorded owner decisions.

## Human review and unresolved decisions

- **OD-9 SC-010 measurement. DECIDED (D12): shared directory.** Byte identity
  applies to files Codex and Claude Code read (manifests, `mcp.json`, `.mcp.json`,
  `launch`, `skills/`, `runtime/`); `package-inventory.json` and `provenance.json`
  change only by added entries. SC-010 is amended accordingly.
- **OD-10 Legacy server name for OpenCode. DECIDED (D13): `agent-braid`.** Same
  default as the other hosts; no duplicate server. Coexistence (for example a
  project `opencode.json` with a legacy entry committed by a teammate, or a
  migration not yet completed) shadows the native plugin; Agent Braid warns and
  the operator resolves it with `plugin legacy` or by updating. The recommendation
  `agent-braid-tooling` was not selected.
- **ADR 0037 adoption.** Proposed; adoption authorizes no implementation by itself.
- T002 findings that contradict R1–R7 return to the owner before T003–T007.

Remote milestone M4.7, issues and Project items are not created.
