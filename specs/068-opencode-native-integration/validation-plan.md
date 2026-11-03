# SPEC-068: Validation plan

Status on `develop` (2026-11-03): procedures 002–010 have deterministic or
disposable-profile evidence, recorded in `evidence/opencode-host-matrix.json` and
`evidence/engineering-checks-develop.json`; procedure_001 (owner review), 011
(documentation review) and 012 (native observation, PR #1031) have none yet. Unit
procedures use fake `opencode`, `codex` and `claude` executables and never start a
model provider. Native procedures run in a disposable OpenCode profile and never
edit the user's configuration. Passing unit procedures does not establish native
behaviour; that is procedure_012.

Commands use the isolated environment: `.venv-speckit/bin/python -m unittest …`.

| Procedure | Scenario | Test target | Expected | Negative controls |
|---|---|---|---|---|
| procedure_001 | SC-001 | `speckit-analyze` report, ADR 0037, surface contract | requirements, tasks and procedures agree; existing contracts unchanged | contract change to `agent-braid-plugin/v0.2`; missing gate |
| procedure_002 | SC-002 | `evidence/opencode-host-matrix.json` (disposable profile) | every row observed or `unobserved`, with version and command | user config touched; Git install alters exec bits, bytes or size |
| procedure_003 | SC-003 | native package test + MCP stdio fixture | core values equal Codex/Claude for the same input | unknown ID, arbitrary root, execution without grant |
| procedure_004 | SC-004 | skill/command listing fixture + `plugin doctor` | six skills and two commands with canonical text; collision reported | shadowing skill named `analyze`; any grant path |
| procedure_005 | SC-005 | setup/registry fixture | `reconnectRequired: true` until reconnect command | automatic reload observed |
| procedure_006 | SC-006 | lifecycle fixture with fake `opencode` | install, update, remove and legacy migration leave documented state | foreign configuration removed; unowned entry removed |
| procedure_007 | SC-007 | `tests/test_plugin_installer.py` | `--host opencode`, `all` and `--dry-run` commands as specified | absent OpenCode; Codex/Claude output changed |
| procedure_008 | SC-008 | legacy lifecycle tests on isolated JSONC destination | owned entry only; comments and foreign bytes kept; idempotent | changed digest, unowned collision, failed write without rollback |
| procedure_009 | SC-009 | MCP envelope and store inspection | envelopes byte-identical with and without `_meta` session ID | session ID present in any stored artifact |
| procedure_010 | SC-010 | native build + inventory/provenance checks | OpenCode package emitted; files Codex/Claude read byte-identical; inventory and provenance only gain entries (D12) | package-name check failure; artifact drift |
| procedure_011 | SC-011 | documentation checks + manual review | consistent OpenCode docs; links resolve | unobserved behaviour claimed |
| procedure_012 | SC-012 | `evidence/native-observation.json` (owner or operator) | install, skills, `analyze-work`, reconnect, removal recorded | inferred observation; missing version |

Repository validation for every change: `quick` after an increment and `pr` on
the stable candidate, through a clean clone while the shared object store fails
the portable-root check.
