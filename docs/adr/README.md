# Architecture decision records

Index of the ADRs in this directory. The Status token is the first word of each ADR's `- **Status:**` line:
`Accepted`, `Proposed`, `Rejected` or `Superseded`, followed by ` — ` and the original text. The Specification
column links the specification named in the ADR itself; `—` means the ADR names none. The template is
[0000-template.md](0000-template.md) and is not listed.

`Proposed` ADRs are unchanged and record who decides: `decision pending: <owner; track>`.

ADR 0024 has two files. [0024-native-ai-plugins.md](0024-native-ai-plugins.md) is the active ADR 0024.
[0024-local-technical-telemetry.md](0024-local-technical-telemetry.md) is a compatibility pointer (resolved 2026-10-20) that only
preserves historical links; the active telemetry ADR is 0025. Nothing is renumbered. The pointer has no
Status line, so its row shows `Pointer` instead of a Status token.

| ADR | Title | Status | Specification |
|---|---|---|---|
| 0001 | [Formalization before production implementation](0001-formalization-before-implementation.md) | Accepted | — |
| 0002 | [Yang–Baxter is a hypothesis, not an assumed property](0002-yang-baxter-is-a-hypothesis.md) | Accepted | — |
| 0003 | [Copyleft licensing and trademark protection](0003-copyleft-and-trademark-protection.md) | Accepted | — |
| 0004 | [Scientific constitutional clarifications](0004-scientific-constitutional-clarifications.md) | Accepted | — |
| 0005 | [Evidence contracts and bounded laboratory](0005-evidence-contracts-and-bounded-laboratory.md) | Accepted | — |
| 0006 | [Shared Spec Kit guardrails for Codex and Claude Code](0006-shared-spec-kit-guardrails.md) | Accepted | — |
| 0007 | [Python reference analyzer before runtime execution](0007-read-only-python-analyzer.md) | Accepted | — |
| 0008 | [Read-only Git and worktree adapter](0008-read-only-git-worktree-adapter.md) | Accepted | — |
| 0009 | [Transparent validation status](0009-transparent-validation-status.md) | Accepted | — |
| 0010 | [Clean publication and portable provenance](0010-clean-publication-provenance.md) | Accepted | — |
| 0011 | [Risk-based validation gates](0011-risk-based-validation-gates.md) | Accepted | [SPEC-010](../../specs/010-risk-validation/spec.md) |
| 0012 | [MIT boundary for vendored Python skills](0012-vendored-python-skills-license-boundary.md) | Accepted | — |
| 0013 | [Isolated Git replay and advisory planning](0013-isolated-git-replay-and-advisory-planning.md) | Accepted | [SPEC-012](../../specs/012-m2-git-replay-planner/spec.md) |
| 0014 | [Contract boundary for parallel integration](0014-parallel-integration-contract.md) | Accepted | [SPEC-012](../../specs/012-m2-git-replay-planner/spec.md) |
| 0015 | [Real-repository M2 validation profile](0015-real-repository-validation-profile.md) | Accepted | [SPEC-013](../../specs/013-m2-real-workload/spec.md) |
| 0016 | [Post-root public provenance supplement](0016-post-root-public-provenance.md) | Accepted | [SPEC-014](../../specs/014-m2-observation-normalizer/spec.md) |
| 0017 | [Bounded structured exchange laboratory](0017-bounded-structured-exchange.md) | Accepted | [SPEC-018](../../specs/018-structured-exchange/spec.md) |
| 0018 | [Private authoring sidecar and disposable decision labs](0018-private-source-sidecar-and-disposable-labs.md) | Accepted | [SPEC-019](../../specs/019-native-predictor/spec.md) |
| 0019 | [Bounded authorized local Git runtime](0019-bounded-local-git-runtime.md) | Accepted | [SPEC-020](../../specs/020-m4-local-git-runtime/spec.md) |
| 0020 | [Complete bounded M4 alpha runtime](0020-bounded-m4-alpha-runtime.md) | Accepted | [SPEC-021](../../specs/021-m4-alpha-runtime/spec.md) |
| 0021 | [Portable tooling integration for Codex and Claude Code](0021-codex-claude-tooling-integration.md) | Proposed — decision pending: founder; no adoption recorded (SPEC-039 M4.5 program) | [SPEC-039](../../specs/039-ai-tooling-program/spec.md) |
| 0022 | [Attribution-correction history equivalence](0022-attribution-correction-history-equivalence.md) | Accepted | — |
| 0023 | [Preserve historical contracts after the second history correction](0023-second-history-correction-equivalence.md) | Proposed — decision pending: founder; history-correction integration | — |
| 0024 | [Historical telemetry ADR reference pointer](0024-local-technical-telemetry.md) | Pointer — to [ADR 0025](0025-local-technical-telemetry.md) (resolved 2026-10-20; not an active ADR) | — |
| 0024 | [Native user-scoped AI plugins](0024-native-ai-plugins.md) | Proposed — decision pending: founder; capability acceptance (SPEC-046) | [SPEC-046](../../specs/046-native-ai-plugins/spec.md) |
| 0025 | [Explicit local aggregate telemetry](0025-local-technical-telemetry.md) | Proposed — decision pending: founder; architectural adoption (SPEC-047) | [SPEC-047](../../specs/047-local-technical-telemetry/spec.md) |
| 0026 | [Pure owned-work validation boundary](0026-pure-owned-work-validation.md) | Accepted | [SPEC-051](../../specs/051-owned-work-evaluation/spec.md) |
| 0027 | [Braid Harness offline foundations](0027-braid-harness-offline-foundations.md) | Accepted | [SPEC-048](../../specs/048-harness-variant-laboratory/spec.md) |
| 0028 | [Closed effectful workload simulation](0028-closed-effectful-workload-simulation.md) | Accepted | [SPEC-024](../../specs/024-effectful-workload-lab/spec.md) |
| 0029 | [Claude-only dynamic workflows component in the native plugin](0029-claude-dynamic-workflows.md) | Proposed — decision pending: founder; adoption in SPEC-052 T033–T036 | [SPEC-052](../../specs/052-claude-workflow-gate/spec.md) |
| 0030 | [Native plugin surface naming](0030-native-plugin-surface-naming.md) | Accepted | [SPEC-054](../../specs/054-plugin-surface-naming/spec.md) |
| 0031 | [Portable MCP prompt names](0031-portable-prompt-names.md) | Accepted | [SPEC-060](../../specs/060-portable-prompt-names/spec.md) |
| 0032 | [Read-only local activity viewer as an opt-in companion](0032-activity-viewer-companion.md) | Accepted | [SPEC-061](../../specs/061-activity-viewer/spec.md) |
| 0033 | [MIT boundary for vendored Three.js](0033-vendored-threejs-mit-boundary.md) | Accepted | [SPEC-061](../../specs/061-activity-viewer/spec.md) |
| 0034 | [System One shadow mode and advisory boundary](0034-system-one-shadow-advisory-boundary.md) | Accepted | [SPEC-066](../../specs/066-system-one-shadow/spec.md) |
| 0035 | [Native Claude laboratory containment](0035-native-claude-laboratory-containment.md) | Accepted | [SPEC-065](../../specs/065-native-claude-containment/spec.md) |
| 0036 | [Assurance profiles and the standing-authorization record](0036-assurance-profiles.md) | Accepted | [SPEC-067](../../specs/067-assurance-profiles/spec.md) |
| 0037 | [OpenCode native plugin](0037-opencode-native-plugin.md) | Accepted | [SPEC-068](../../specs/068-opencode-native-integration/spec.md) |
| 0038 | [analyze-work request contract](0038-analyze-work-request-contract.md) | Accepted | [SPEC-069](../../specs/069-aim-request-authoring/spec.md) |
| 0039 | [Braid Lightning optimization boundary](0039-braid-lightning-boundary.md) | Accepted | [SPEC-070](../../specs/070-braid-lightning-foundations/spec.md) |
| 0040 | [Vendoring microsoft/agent-lightning (MIT) into AGPL modules](0040-braid-lightning-mit-vendoring.md) | Accepted | [SPEC-070](../../specs/070-braid-lightning-foundations/spec.md) |
| 0041 | [Consent, redaction and retention for content-bearing traces](0041-braid-lightning-content-traces.md) | Accepted | [SPEC-074](../../specs/074-lightning-trace-consent/spec.md) |
| 0042 | [Local weight training for Braid Lightning (deferred)](0042-braid-lightning-local-weight-training.md) | Proposed — decision pending: founder go/no-go; deferred (SPEC-076) | [SPEC-076](../../specs/076-lightning-local-grpo/spec.md) |
| 0043 | [Read-only harness views over the plugin MCP facade](0043-harness-mcp-readonly-surface.md) | Rejected | [SPEC-077](../../specs/077-harness-mcp-readonly/spec.md) |
| 0044 | [Harness portability tiers and a skill-first harness surface](0044-harness-portability-tiers-skill-surface.md) | Accepted | [SPEC-080](../../specs/080-harness-skill-every-host/spec.md) |
| 0045 | [Hybrid harness evaluation substrate (Harbor containers plus a macOS shadow)](0045-hybrid-harness-evaluation-substrate.md) | Proposed — decision pending: founder; SPEC-084 T001 review | [SPEC-084](../../specs/084-harbor-evaluation-substrate/spec.md) |
