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
| [044](../044-ai-tooling-evaluation/spec.md) | Evaluation and closure | Registered protocol; stable 040–043 candidate | Host receipts, controls, complete-cost comparison, decision packet |

Independent engineering can advance once its consumed contract is stable.
Dependency labels do not authorize concurrent agents, provider expenditure,
new infrastructure, scientific capture or founder acceptance.

## M4 relationship

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

First deliver a reviewable source PR containing these six specs, their task
lists/assurance records, proposed ADR and mapping. Record review findings without
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
