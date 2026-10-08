# AI tooling integrations

**Status — 2026-10-08:** [M4.5](https://github.com/jayanez/agent-braid/milestone/19) is Open, adjacent to M4, with six spec issues and 60 linked task subissues. Six draft
Spec Kit packages define 48 requirements, 48 acceptance scenarios and 60 unchecked
implementation tasks. An unmerged experimental implementation candidate is now present; paired evidence,
actual host observations and acceptance remain pending. Administrative tracking is registered; the [registration record](../../specs/039-ai-tooling-program/administrative-registration.md) links each parent and its work queue. [ADR 0021](../adr/0021-codex-claude-tooling-integration.md) is proposed.

## Start here

Start the experimental candidate with [installation](INSTALL.md),
[presentation](../ai-tooling-presentation.md) and [evaluation preparation](EVALUATION.md).
The [implementation map](../../specs/039-ai-tooling-program/implementation-status.md)
retains all work packages and pending paired evidence. The `agent-braid tooling`
command group provides stdio serving, previewed receipt-owned lifecycle operations,
read-only diagnostics and presentation/export of already obtained values.
Capture preparation also provides [local measurement primitives](MEASUREMENTS.md),
[one-shot host event parsing](HOST_EVENTS.md), and
[single-dispatch session coordination](SESSIONS.md),
[verified cost reconciliation](COSTS.md),
[bounded process supervision](SUPERVISOR.md), and
[explicit host adapters](HOSTS.md). These components preserve unavailable costs
and require external authenticators, frozen configuration and verified live
telemetry. Their controls use synthetic owned processes; actual host capture
and the registered evaluation remain pending.
Actual host trust/authentication, complete comparisons and founder acceptance
are still separate gates. Plain text/ASCII graphs work without a browser;
JSON retains complete core values after any artifact reconstruction.

The existing bounded stdio MCP runtime is documented in the
[alpha quickstart](../../specs/021-m4-alpha-runtime/quickstart.md). The
[owned fixture tutorial](../../examples/runtime/README.md) demonstrates analysis,
grants, execution and recovery using current local commands.

The planned M4.5 journey lets a developer ask Agent Braid to examine proposed
work, explain dependencies/conflicts and unknowns, prepare an advisory plan,
execute an already granted bounded batch, recover an interruption and export
the verified result with its evidence and limits.

The first targets are **Codex local CLI and Claude Code local CLI** on macOS
arm64 at recorded exact versions. Linux x86_64 is the initial package/protocol/core
reproduction target. See the [capability and host matrix](../../specs/039-ai-tooling-program/capability-matrix.md)
for the required observations and support boundaries.

## Specification map

| Area | Planned deliverable | Source |
|---|---|---|
| Program | Scope, dependencies, capability matrix, research and governed tracking | [SPEC-039](../../specs/039-ai-tooling-program/program.md) |
| MCP | Shared optional SDK adapter, typed tools/resources/prompts and CLI parity | [SPEC-040](../../specs/040-portable-mcp-surface/spec.md) · [Interface contract](../../specs/040-portable-mcp-surface/contracts/interface.md) |
| Skills | Analyze, plan, execute, recover and evidence workflows | [SPEC-041](../../specs/041-ai-tooling-skills/spec.md) · [Bundle contract](../../specs/041-ai-tooling-skills/contracts/skill-bundle.md) |
| Lifecycle | Isolated reusable package, explicit user/project configuration, doctor, update and uninstall | [SPEC-042](../../specs/042-ai-tooling-packaging/spec.md) · [Lifecycle contract](../../specs/042-ai-tooling-packaging/contracts/lifecycle.md) |
| Developer journey | Chat explanations, interaction graph and offline Markdown/SVG/HTML evidence exports | [SPEC-043](../../specs/043-ai-tooling-journey/spec.md) · [Presentation contract](../../specs/043-ai-tooling-journey/contracts/presentation.md) |
| Evaluation | Actual host receipts, controls, complete costs and CLI/MCP/MCP-plus-skills comparison | [SPEC-044](../../specs/044-ai-tooling-evaluation/spec.md) · [Prospective protocol](../../specs/044-ai-tooling-evaluation/evaluation-protocol.md) |

The proposed interface defaults to analysis. Runtime activation requires explicit
configuration and the existing operator grant policy. Grant issuance stays outside
model-callable tools and skills; runtime work retains the existing private,
fixed-patch scope. M4.5 acceptance is separate from M4's whole-milestone acceptance
and historical G4 NO-GO.

## Contribution and delivery

The existing generated `.agents/skills/` and `.claude/skills/` adapters implement
the repository's [Spec Kit contribution workflow](../development/SPEC_KIT.md).
M4.5's five candidate product skills have their canonical home at
`integrations/agent-braid/skills/`, with minimal host packaging. Implementation
follows the linked task lists and consumed-contract reviews.

The [delivery record](../../specs/039-ai-tooling-program/delivery-status.md),
[issue drafts](../../specs/039-ai-tooling-program/issue-drafts.md) and
[milestone index](../development/SPEC_MILESTONE_INDEX.md) expose preparation and
tracking state. Source validation, independent review, implementation evidence,
host capture, human interpretation and founder acceptance have separate records.

## Future environments

Cursor, VS Code/GitHub Copilot, OpenCode and pi are deferred. The
[program's five future routes](../../specs/039-ai-tooling-program/program.md#five-future-routes)
also cover AI applications/orchestration, expanded execution, coordination across
tools and embedded visual interaction. Each route needs its own selected scope,
contracts, observations and acceptance decisions.
