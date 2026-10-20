# M4.5 — AI tooling integrations for Codex and Claude Code

**Status:** [Open](https://github.com/jayanez/agent-braid/milestone/19) implementation program, 2026-10-08. Source preparation is
authorized. Product implementation, observations and acceptance follow the tasks
and explicit gates below. No capability or milestone closure is claimed here.

## User outcome

From either supported host a developer can ask Agent Braid to examine proposed
work, see dependencies/conflicts and unknowns, prepare an evidence-backed plan,
inspect exactly what needs operator permission, execute an already granted bounded
batch, recover an interruption and export the verified result with its limits.
Installation and diagnostics make this workflow reproducible beyond this repository.

## Portfolio and dependency order

| Spec | Responsibility | Depends on | Deliverable |
|---|---|---|---|
| [039](spec.md) | Program and capability contract | Current M1/M2 and ADRs 0019/0020 | Research, matrix, ADR, tracking and closure map |
| [040](../040-portable-mcp-surface/spec.md) | Portable MCP surface | 039 contract review | SDK adapter, typed tools/resources/prompts, CLI parity |
| [041](../041-ai-tooling-skills/spec.md) | Five product skills | 039, 040 schemas | Analyze, plan, execute, recover, evidence workflows |
| [042](../042-ai-tooling-packaging/spec.md) | Packaging and lifecycle | 040 interface, 041 layout | Optional extra, host assets, install/configure/doctor/update/uninstall |
| [043](../043-ai-tooling-journey/spec.md) | Developer journey | 040, 041, 042 | Chat explanations, graph, offline Markdown/SVG/HTML |
| [044](../044-ai-tooling-evaluation/spec.md) | Evaluation and closure | Registered protocol; stable 040–043 and validated 047 for the future new-candidate pilot | Host receipts, controls, complete-cost comparison, decision packet |
| [046](../046-native-ai-plugins/spec.md) | Native AI plugins | Existing 040/042 interfaces | Self-contained runtime, workspace registry, setup and separately tracked candidacy |
| [047](../047-local-technical-telemetry/spec.md) | Local technical telemetry | Existing 040/042 interfaces | Default-off collector, bounded storage, manual exchange and validation |

Independent engineering can advance once its consumed contract is stable.
Dependency labels do not authorize concurrent agents, provider expenditure,
new infrastructure, scientific capture or founder acceptance.

## M4 relationship

The founder accepted bounded M4 alpha engineering/evaluation separately on
2026-10-09; [PR #471](https://github.com/jayanez/agent-braid/pull/471) is
included in predecessor commit `9dfd9fdf52e688e7225af1f7644f41b6ba92b780`.
[Milestone #6](https://github.com/jayanez/agent-braid/milestone/6) was
verified closed with 46 closed issues and none open on 2026-10-09. This
separate decision preserves negative utility, historical SPEC-021 G4 NO-GO
and deferred capabilities; it grants no M4.5 capture or acceptance.

M4.5 is contiguous to M4 in the product roadmap and consumes its existing bounded
runtime. Engineering does not require a favorable M4 speedup result or new M3
research. Actual runtime support requires the consumed M4 contracts and refinement
to remain valid for the exact adapter. It cannot close M4, supersede SPEC-038 source
rights, reuse another task's capture permission or turn SPEC-021 G4 NO-GO into GO.
M4.5 utility concerns integration usability; any runtime speed claim needs its own
accepted measurement. See [capability matrix](capability-matrix.md).

## V1 acceptance

1. Both hosts discover and invoke the supported interface on macOS arm64 at
   recorded exact versions. Linux x86_64 reproduces package/protocol/core controls;
   that is not a Linux real-host claim.
2. AIM/Git/worktree analysis explains conflict/conditional/unknown observations,
   proposed plans remain advisory and runtime writes require existing exact grants.
3. Five skills lead to the same typed contract in both hosts, with no hooks or
   grant issuance paths. Host wrappers carry only necessary integration metadata.
4. Installation in an isolated environment, explicit configuration, diagnosis,
   repeat installation, update and removal preserve unrelated skills/configuration.
5. Each mandatory journey retains inputs, candidate/environment identities, raw
   outputs, structured evidence and deterministic exports; unknowns and exclusions
   remain visible. A malformed/stale input or invalid grant cannot produce success.
6. All deterministic negative controls pass, clean-room evidence and real-host
   observations are separate, utility is reported under the preregistered protocol,
   and the founder records bounded acceptance/closure.

An unfavorable comparison is a valid result. It cannot support a positive utility
claim; the decision packet may reject or narrow product adoption. Mock clients
cannot satisfy criterion 1.

## Delivery and governed tracking

The original delivery comprised six specs, their task lists/assurance records, proposed ADR and mapping. The current eight-spec portfolio is described below; no new PR, integration or publication is authorized by this record. Record review findings without
inventing approval. Preserve current draft snapshots during this linear-history
source integration; freeze the integrated develop candidate for later human
acceptance as described in [integration provenance](analysis.md#integration-provenance).
After source integration into clean develop, audit the exact
new milestone, six spec parents and their stable task subissues; approve/apply the
digest under GITHUB_TRACKING.md and require a subsequent `operations: []` audit.
Keep private Project membership and Review pending status as a separate check.
No unrelated tracking drift is included in M4.5.

M4.5 is registered as milestone **#19**, with six parent issues and 60 task subissues. The [administrative registration record](administrative-registration.md) records the scoped audit and Project check. Future reconciliations use the registered number and their exact reviewed digest; bootstrap allowlists apply only to genuinely missing new IDs.
See [issue drafts](issue-drafts.md) and individual task lists.

Product code follows bounded PR slices: protocol and analysis, runtime bridge,
skills, packaging, exports, then stable-candidate observation/evaluation.
ADR adoption, specific API review, actual host execution, disclosure/publication,
merge and final closure retain their applicable decisions.

## Five future routes

| Route | Candidates | Entry requirement |
|---|---|---|
| Additional development environments | Cursor, VS Code/GitHub Copilot, OpenCode, pi | Host capability/permission matrix, new adapter observations, lifecycle controls |
| AI applications and orchestration | Agent SDK consumers and optional remote MCP | Selected consumer, auth/transport/privacy contracts, bounded conformance |
| Expanded execution | Source ref promotion, code/test execution, API effects | New effect/isolation/rollback contracts and explicit operator authority |
| Coordination across tools | Shared plans and resource ownership | Identity, concurrency, idempotency and recovery contract |
| Embedded visual interaction | MCP Apps or host-native interactive views | UI/security/privacy contract and real host support |

These are documented options. They add no v1 tasks, compatibility claims or
execution authority. No provider ranking is asserted.

## Current local telemetry extension — 2026-10-16

The current portfolio has eight specs: the original 039–044, [046 native plugins](../046-native-ai-plugins/spec.md) and [047 telemetry](../047-local-technical-telemetry/spec.md). SPEC-047 consumes the existing 040/042 interfaces and owns default-off local numeric aggregation, bounded SQLite retention and manual exchange. It must be validated before a future new-candidate pilot; it does not depend on completing native evaluation. [The global matrix](../../docs/tooling/M45_ALIGNMENT.md) separates technical dependencies, observations, review and acceptance, including M1/M2/M4 and SPEC-034–037/045.

Original SPEC-039/040/042 acceptance and all frozen receipts remain historical. [Previously approved SPEC-044/T004 closure](../044-ai-tooling-evaluation/t004-bounded-closure-reconciliation.md) is incorporated without reopening A/T004 or repeating reproduction. SPEC-044/T017 and T018 remain pending. PR #509 was observed draft/open at `482fbcc` before the rewrite; its changes are now integrated in rewritten develop `e474320e`. The source modules are present, but their presence does not supply authenticated native observations or close registration/admission gates. The integration candidate has its own validation boundary; [the existing b2cf Luna review](../047-local-technical-telemetry/integration-review.md) is retained without repetition.

This delivery prepares source tracking for milestone #19, one SPEC-047 parent, ten subissues and two SPEC-044 follow-ups. Sources are local and unpublished. Review, integration, scoped digest audit/apply with exact new-record keys, readback and private Project verification remain deferred until separately authorized. No remote issue is created or closed by this local source update.
