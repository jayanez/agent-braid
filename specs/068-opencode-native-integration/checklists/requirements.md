# Specification quality checklist: SPEC-068

A checked item records that the artifact contains the element; it is not
validation, approval or evidence that the host behaves as documented. Items
marked with an analysis finding (A-n) stay open until the finding is resolved;
A-1 to A-9 were resolved in the artifacts on 2026-11-03 (A-1 by owner decision D12).
Reviewed against `develop` on 2026-11-03 after T002–T009 merged; the one remaining
unchecked item below (CHK-022) depends on a gate that is still open.

## Requirement clarity

- [x] CHK-001 Purpose, scope, exclusions and the SPEC-039 route are stated (`spec.md` §Purpose and scope).
- [x] CHK-002 Owner decisions D1–D11 are recorded with dates (`spec.md` §Clarifications).
- [x] CHK-003 SC-010 agrees with the plan's shared-directory design. Decided D12 (`spec.md` REQ-010, `plan.md` §Human review; finding A-1).
- [x] CHK-004 Surface contract does not both forbid file writes and require the entry to "record" collisions (`contracts/opencode-surface.md` §MCP server; finding A-2 resolved 2026-11-03).
- [x] CHK-005 Host permission configuration for `agent-braid_*` and `agent-braid-tooling_*` tools is specified or explicitly excluded (both contracts; finding A-6).
- [x] CHK-006 Default legacy server name and its collision rationale are stated (`contracts/opencode-legacy-profile.md` §Owned entry; decided D13, `agent-braid` with a `native_plugin_shadowed` warning).

## Normative references

- [x] CHK-007 Constitution articles, GOVERNANCE, claim discipline and ADRs 0021/0024/0030/0031 are cited (`spec.md` §Authorities; `assurance.json` `articles`, `references`).
- [x] CHK-008 ADR 0037 exists and states that adoption authorizes nothing by itself (`docs/adr/0037-opencode-native-plugin.md`). On `develop` it reads Proposed; the owner adopted it on 2026-11-03 (D14) and PR #1030 records Accepted.
- [x] CHK-009 Current authority snapshot matches the tree (`validate_spec_kit` passed on `develop` at 38c0b268, 2026-11-03; PR #1030 refreshes the ADR 0037 hash lines when it records the ADR status).

## Acceptance coverage and traceability

- [x] CHK-010 Each of REQ-001…REQ-012 has one scenario and one procedure (`spec.md`, `validation-plan.md`, `assurance.json`).
- [x] CHK-011 Task ownership of REQ-006 matches the work: spec names T003, T007; native install/update/remove is in T006 and T010 (`spec.md` REQ-006, `tasks.md`; finding A-3).
- [x] CHK-012 T007's file list includes `agent_braid/plugin_cli.py` (`plugin legacy --host` choices) (`tasks.md` T007; finding A-4).
- [x] CHK-013 T005's configuration read (explicit `skills` entries in JSONC) has a dependency on the JSONC scanner of T007, or a stated simpler reader (`tasks.md` T005; finding A-5).
- [x] CHK-014 T006 dependency on PR #983 (`install.sh --host all`) is stated; this clone's `install.sh` still offers `both` only (`tasks.md` T006; finding A-7).
- [x] CHK-015 T002's row list covers the configuration-path facts T007 relies on (XDG paths on macOS and Linux, `opencode.json` vs `.jsonc` precedence) (`tasks.md` T002/T007; finding A-8).
- [x] CHK-016 SC-003's "when OpenCode starts the server" is split between the stdio fixture (T003) and the native observation (T010) (`spec.md` SC-003; finding A-9).

## Negative controls

- [x] CHK-017 Each procedure lists negative controls (`validation-plan.md`).
- [x] CHK-018 Both contracts list negative controls, including Codex/Claude byte checks (`contracts/`).
- [x] CHK-019 Tasks state negative controls per implementation task (`tasks.md` T002–T008).

## Evidence provenance

- [x] CHK-020 Planned and obtained evidence are separate fields (`assurance.json`). Obtained: SC-002 (host matrix) and SC-003–SC-010 (`evidence/engineering-checks-develop.json`, fixtures and fake executables, run 2026-11-03). Empty: SC-001, SC-011, SC-012.
- [x] CHK-021 Host facts are labelled documented (OpenCode 2.1.2 docs) until T002/T010 observe them (`research.md`, `plan.md`). T002 observed 2.1.4 on macOS arm64 (`research.md` §T002 findings); rows 04b, 05b, 09b and 12b and every T010 item stay unobserved.
- [ ] CHK-022 Owner review record exists and is bound to a frozen commit — pending T001. The owner adopted ADR 0037 on 2026-11-03 (D14); the binding to a frozen commit stays with the T011 candidate freeze (PR #1030).

## Scientific boundaries

- [x] CHK-023 Engineering only; no hypothesis and no scientific claim (`spec.md` §Scientific boundaries; `tasks.md` §Limits).
- [x] CHK-024 Platform targets are not compatibility claims until REQ-012 (`spec.md`).

## Compatibility

- [x] CHK-025 `agent-braid-plugin/v0.2`, `agent-braid-tooling/v0.2`, SPEC-047, SPEC-066 and Codex/Claude receipts are declared unchanged (`spec.md`, ADR 0037).
- [x] CHK-026 Host assets list change (`hosts.json`) is declared additive (`contracts/opencode-legacy-profile.md` §Asset manifest).
- [x] CHK-027 The per-host table refactor in `tooling_install.py` is covered by Codex/Claude byte tests (`tests/test_tooling_install_golden.py`, `tests/test_tooling_install_opencode.py`, merged in PR #1019; `evidence/engineering-checks-develop.json`).
