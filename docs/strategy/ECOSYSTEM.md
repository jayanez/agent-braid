# Ecosystem map

This map is a positioning aid, not a claim of feature parity or superiority.
Entries are based on first-party descriptions and must be refreshed through the
[research radar](../../research/radar/README.md).

| Layer | Representative systems | Primary concern | Agent Braid relationship |
|---|---|---|---|
| Orchestration | [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/multi_agent/), [Anthropic multi-agent research](https://www.anthropic.com/engineering/multi-agent-research-system) | Agent delegation, handoffs, coordination and parallel work | Consume recorded plans/traces; do not replace orchestration |
| Protocols | [A2A](https://a2a-protocol.org/latest/specification/), MCP | Interoperable tasks, artifacts, messages and tool access | Map effect, identity, version and idempotency metadata into AIM without creating parallel semantics |
| Observability and evaluation | [NVIDIA NeMo Agent Toolkit](https://docs.nvidia.com/nemo/agent-toolkit/latest/) and runtime-native traces | Trace, profile, evaluate, and debug behavior | Attach portable concurrency evidence and ordering analysis to traces |
| Guardrails and policy | Runtime permissions, policy engines, sandboxes | Constrain allowed behavior | Produce evidence for a policy decision; never authorize execution itself |
| Concurrency control | Transactions, serializability, optimistic control, Git merge | Preserve correctness under shared-state interaction | Apply conservative resource/effect analysis and version constraints |
| Formal and algebraic methods | Rewriting, confluence, partial orders, braid/Yang–Baxter research | State and prove properties in defined domains | Maintain a bounded laboratory; treat analogy as hypothesis until proved |

Recent unreviewed work such as [CoAgent](https://arxiv.org/abs/2606.15376)
and the position paper [Multi-Agent Systems Should Prioritize Concurrency
Control](https://arxiv.org/abs/2608.18092) is directly adjacent. Agent Braid has
not reproduced either paper. They enter the M2 comparison backlog as source
claims, not evidence of Agent Braid's novelty, correctness or performance.

MCP's current security guidance identifies authorization, session, local-process
and SSRF risks. These reinforce the existing rule that external trace ingestion
and write-capable adapters require dedicated privacy and security review; protocol
support alone cannot satisfy that gate.

## Competitive gap under test

The proposed [M4.5 integration program](../tooling/README.md) selects Codex and
Claude Code local CLIs as its first developer hosts. It combines MCP access,
portable workflow skills, explicit installation/configuration and evidence
presentation. The [research register](../../specs/039-ai-tooling-program/research.md)
records the official sources behind these design choices. Product implementation,
compatibility observations and usability evaluation remain pending.

Cursor, VS Code/GitHub Copilot, OpenCode and pi are documented future routes.
Additional hosts, remote consumers and interactive embedded views require their
own contracts and observations before any support claim.

The hypothesis is that teams need portable, evidence-carrying analysis between
orchestration and execution policy. This is not yet established market demand.
It will be tested through integrations, independent reproductions, benchmark
coverage, contributor activity, and interviews. A negative result should narrow
or invalidate the thesis rather than be reframed as success.

### Claude Code dynamic workflows (M4.6, untested)

Per Claude Code's [official documentation](https://code.claude.com/docs/en/workflows),
dynamic workflows script many agents and can isolate each in a Git worktree. The
documentation describes no automatic merge and no conflict detection across those
worktrees, so detection and integration remain the user's task. This is a reading
of vendor documentation, not an observation by this project.

Third-party tools address part of that gap at file or text level:
[clash](https://github.com/clash-sh/clash) reports pairwise `git merge-tree`
conflict detection across worktrees, and
[mcp_agent_mail](https://github.com/Dicklesworthstone/mcp_agent_mail) reports
advisory path leases. Neither was observed reasoning about declared effects,
read/write hazards or order independence. Their behavior is not reproduced here.

Agent Braid's differentiation hypothesis is that effect-level evidence, including
read/write hazards and order-independence findings, surfaces problems that a
`git merge-tree` baseline does not. That hypothesis is untested. It is gated by the
preregistered M4.6 gate G0, and a negative or inconclusive result narrows or closes
it. Today's analysis is commit-level, with coverage limits and a documented
false-negative case; no speed claim is made, since parallel runtime speedup is
NO-GO in earlier evaluations. Agent Braid consumes recorded workflow output and
does not replace orchestration. Records:
[radar entries](../../research/radar/2026-10-23-claude-workflows.json),
[adoption track AT-2026-006](../../research/adoption/2026-09-initial-triage.json),
[SPEC-052](../../specs/052-claude-workflow-gate/spec.md) and
[SPEC-053](../../specs/053-claude-transcript-trace-adapter/spec.md).

### Orchestrator coordination prior-art pass (M4.6, 2026-10-24)

A dated, read-only pass covered tools that coordinate parallel Claude Code
agents. The query set, per-capability classification, limits and sources are
recorded in the [radar snapshot](../../research/radar/2026-10-24-claude-orchestration.json)
(RAD-2026-016 to RAD-2026-033) and adoption track AT-2026-007 in the
[track register](../../research/adoption/2026-09-initial-triage.json). READMEs
were read, no tool was installed, and no behavior was reproduced. The field is
crowded and moving: several relevant tools in the pass were absent from the
2026-10-23 radar.

Classification for Agent Braid, by capability:

- Behind: stuck-agent detection and recovery, messaging and inboxes, merge queues
  with verification gates ([Gas Town](https://github.com/gastownhall/gastown)
  Witness and Refinery, [SVRF](https://github.com/nybarius/SVRF)), durable claim
  and audit ledgers ([Beads](https://github.com/gastownhall/beads)), path leases
  and seals ([mcp_agent_mail](https://github.com/Dicklesworthstone/mcp_agent_mail),
  [agent-coord](https://github.com/ThatHunky/agent-coord),
  [git-kura](https://github.com/tooppoo/git-kura), whose repository was
  confirmed on 2026-10-24 at 0 stars with a last push on 2026-09-14 and whose
  seal behavior is known from its README only), live textual prediction
  (Clash), and symbol-level overlap
  ([DriftWatch](https://github.com/Vignesh-P-C/DriftWatch)); Agent Braid
  resources are exact strings.
- Parity: hook-based blocking of file edits, declared-footprint pre-flight
  scheduling ([OpenWeft](https://github.com/NeuraCerebra-AI/openweft),
  [Orchestune](https://github.com/Saltmu/orchestune)), and, for the integration
  stage, combined-tree checks that also name missing evidence
  ([Radar](https://github.com/Jake-Network/radar)). The last means reporting
  uncertainty, including unknown as a result, is not by itself a differentiator
  and is not claimed as one. Radar was confirmed on 2026-10-24 at 2 stars with a
  last push on 2026-10-17.
- Complementary: syntax-aware textual merge ([Mergiraf](https://codeberg.org/mergiraf/mergiraf)).
- Candidate differentiators, each bounded and untested: declared read/write
  effect hazards with explicit coverage (near-neighbors that were not ruled out:
  [TeamBus](https://github.com/Beastburner/teambus) reports contract consumers
  blocked until they commit and a conflict check over contract-consumer and
  import relations, and Orchestune reports shared-contract risks; both are
  consumer-side checks, their READMEs do not state coverage, and nothing was
  reproduced); order-independence evidence from replay
  of at most four operations; and declared-versus-observed envelope receipts with
  stated observation coverage (exact-path receipt, Article 13 class
  1-syntactic; pre-flight, recovery and isolation audit are class 0-heuristic;
  never a guarantee). Unknown as a result is not a standalone differentiator.
  Only the combination of an Article 13 compatibility class, pairwise
  classification that includes unknown, declared read/write hazards and the
  declared-versus-observed receipt is retained, and it is itself untested. A
  compatibility class on every output and an audit-first enforcement ladder are
  small, easily copied and untested, so they are not listed as differentiators.
  Read-set validation exists in the literature (for example S-Bus,
  arXiv:2605.17076v1, identified from a search excerpt on 2026-10-24 and not read
  in full), so any claim concerns application to Git worktrees and Claude Code
  agents, not a new technique. Percentage figures about agent over-claiming and
  benign races that circulated in the research digest are unverified and are not
  used; the identifiers actually checked are listed in the radar snapshot under
  literatureReferences.

The official Claude plugin marketplace snapshot (315 plugins) returned no plugin
whose name or description targets multi-agent file ownership or conflict
evidence under the keyword filter recorded in the snapshot; this does not cover
other plugin directories.

Bounded claim wording for any later text: "In a dated pass on 2026-10-24 (query
set recorded in the radar snapshot), no surveyed README of a shipped Claude Code
plugin or coordination tool was found that states read-set validation with
explicit coverage, or that provides order-independence evidence from bounded
replay. TeamBus and Orchestune describe consumer-side or shared-contract checks
that may be near-neighbors; their READMEs were read and their behavior was not
reproduced. This is absence within the surveyed set, not a statement about the whole
market, not a claim of novelty over the literature, and not evidence of user
demand." The words
unique, only, first, nobody offers and any speed term are not used. The pass is
repeated before publication wording, before SPEC-058 release and at M4.6
closure. Interoperation with these tools is optional and untested: Agent Braid
could read their state as declared or observed inputs, or serve as an evidence
step for a verification gate, but no adapter is implemented here; deferred input contracts exist in SPEC-057
and are sketched in SPEC-059. Agent Braid does
not launch, message as, resume or authorize sessions, so the fleet managers
above are not competitors on that axis.

## Adapter rule

Adapters for generic traces, OpenAI Agents, MCP, A2A, or NeMo must preserve:

- operation and attempt identity;
- resource/effect meaning and coverage status;
- dependency and version information;
- evidence provenance and hashes;
- unknown or unsupported fields without inventing certainty.

An adapter translates to AIM. It cannot create a second compatibility model or
raise an assurance class merely because the source is trusted.
