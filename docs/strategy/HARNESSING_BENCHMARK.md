# Harnessing benchmark (2026-11)

Status: dated research snapshot, accessed 2026-11-22. It is a positioning and planning
aid. It is not a claim of parity, superiority or novelty, and it does not adopt any
technology. Vendor facts change fast: re-check every row before quoting it. Provenance
and claim levels per source are in
[research/radar/2026-11-22-harnessing.json](../../research/radar/2026-11-22-harnessing.json).
Owner decisions taken on this basis are listed at the end. They become binding only
through the ADRs and specs that cite them.

## Question

Is the Agent Braid harness layer available in every host where the plugin is
installed? How do established AI SDLC systems handle harnessing: variant evaluation,
promotion, isolation, telemetry, and exposure across hosts?

## Agent Braid today (develop `f90eb58a`, read from code)

| Surface | Claude Code | Codex | OpenCode |
|---|---|---|---|
| `agent-braid harness` CLI (10 commands, `agent_braid/harness_cli.py`) through the plugin `launch` | yes | yes | yes |
| Harness skill or MCP tool | no (7 fixed skills; SPEC-077 not published) | no | no |
| Native harness sessions | lab only (SPEC-065 containment, owner-run launchers) | refused (`NativeCodexHost`) | none (not in the harness `HOSTS`) |
| Harness telemetry | develop only (#1405); not in alpha.9 | same | same |

An agent reaches the harness only if someone tells it to run the plugin `launch`.
Pi and ThinkRail are not mentioned anywhere in the repository.

## Findings by dimension

### 1. Distribution across hosts

- **The portable layer is converging on Agent Skills plus MCP plus AGENTS.md.**
  - Anthropic donated [Agent Skills](https://agentskills.io) to the Linux Foundation's
    Agentic AI Foundation (AAIF), which also hosts MCP and AGENTS.md
    ([Anthropic](https://www.anthropic.com/news/donating-agent-skills-to-the-agentic-ai-foundation),
    [Linux Foundation](https://linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation)).
  - Only `name` and `description` are fully portable. `allowed-tools` is experimental.
    Host dependencies go in `compatibility`
    ([AAIF porting guide](https://aaif.io/blog/how-to-move-a-skill-from-one-coding-agent-to-another)).
- **Each host adds its own native layer:**

  | Host | Native layer |
  |---|---|
  | Claude Code | `.claude-plugin/plugin.json`: skills, agents, hooks, MCP/LSP, output styles, experimental evals ([reference](https://code.claude.com/docs/en/plugins-reference)) |
  | Codex | Root `plugin.json` with `extensions.com.openai`. Also accepts Claude-compatible manifests, reads `.claude-plugin/marketplace.json`, aliases `CLAUDE_PLUGIN_ROOT`. Skills under `.agents/skills` ([build plugins](https://developers.openai.com/codex/plugins/build.md), [skills](https://learn.chatgpt.com/docs/build-skills)) |
  | OpenCode | npm plugins (`opencode plugin add`), `mcp.servers`, `skills` (also reads `.claude/skills`). The schema now uses plural, list-shaped keys ([config](https://opencode.ai/docs/config), [MCP](https://opencode.ai/docs/mcp-servers)) |
  | Pi | Pi packages (`pi install npm:<pkg>`) whose `package.json` declares `extensions`, `skills`, `prompts` and `themes`. TypeScript extension API with about 30 lifecycle events. Four core tools and a system prompt under 1,000 tokens ([Pi README](https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/README.md), [packages](https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/packages.md)) |
  | ThinkRail (JetBrains incubator, Apache-2.0, v0.4.0 on 2026-11-12) | A thin host that runs Pi in-process. Installs any Pi package, connects the MCP servers in Pi's `mcp.json` with per-call approval, imports Claude and Codex skills, and isolates each workspace in a git worktree ([GitHub](https://github.com/JetBrains/thinkrail)) |
  | Gentle AI | A Go configurator that writes native configuration for 17 or more hosts: Engram memory MCP, ODD workflow, receipt-driven review, skills ([GitHub](https://github.com/Gentleman-Programming/gentle-ai)) |

- **Evaluation platforms ship skills or MCP so the agent can query them from inside
  the host.**
  - Langfuse: MCP plus a skill ([MCP](https://langfuse.com/docs/api-and-data-platform/features/mcp-server)).
  - LangSmith: remote MCP plus a CLI built for coding agents ([MCP](https://docs.langchain.com/langsmith/langsmith-remote-mcp)).
  - Braintrust: MCP ([MCP](https://docs.braintrust.dev/integrations/developer-tools/mcp)).
  - Phoenix: a plugin with MCP and five skills ([coding agents](https://arize.com/docs/phoenix/integrations/developer-tools/coding-agents)).
  - promptfoo: a stdio MCP server and four skills ([skills](https://www.promptfoo.dev/docs/integrations/agent-skill/)).
- **The minimalist position.** Zechner measures large MCP servers at 7–9 % of the
  context window and prefers skills plus CLI
  ([post](https://mariozechner.at/posts/2025-11-30-pi-coding-agent/)). OpenAI keeps
  AGENTS.md as a table of contents of about 100 lines
  ([harness engineering](https://openai.com/index/harness-engineering/)).

**Gap.** Agent Braid has no agent-discoverable harness surface. A skill plus the CLI
fits every host above, Pi included, without adding a per-session MCP cost.

### 2. Variant evaluation

- **Claude Code `claude plugin eval`.**
  - Each case directory has graders of six types: regex, tool_used, tool_order,
    file_exists, llm and baseline.
  - It runs 3 times per arm and compares a with-plugin arm against a no-plugin
    ablation.
  - CI gets JSON `schemaVersion: 1`, exit codes, replay mocks and a pinned model.
  - Δ never changes the exit code. Scores are "advisory" when hooks or real MCP
    servers run outside the sandbox.
  - skill-creator runs a separate with/without A/B for skills.
  - Source: [plugin evals](https://code.claude.com/docs/en/plugin-evals).
- **Codex** documents no first-party harness evaluation. Plugins are tested through
  local marketplaces ([build plugins](https://developers.openai.com/codex/plugins/build.md)).
- **Harbor / Terminal-Bench 2.0.**
  - About 45 agent adapters, including claude-code, codex, opencode, opencode-v2 and
    pi.
  - One container per trial, `-k` attempts, and per-phase network policies (public,
    no-network, allowlist) enforced by an nftables sidecar.
  - ATIF trajectories.
  - Terminal-Bench 2.0: 89 tasks, at least 5 runs per agent–model pair, 95 % CIs,
    an oracle solution plus an exploit agent per task, and two auditors.
  - The paper's own self-assessment calls its canary string "largely symbolic".
  - Sources: [Harbor](https://docs.harborframework.com/), [agents](https://docs.harborframework.com/agents/pre-integrated-agents.md),
    [network policies](https://docs.harborframework.com/tasks/network-policies.md),
    [TB 2.0 paper](https://arxiv.org/html/2601.11868v1).
- **Inspect AI (UK AISI).**
  - One sandbox per sample.
  - `sandbox_agent_bridge` runs real agent CLIs and proxies every model call through
    the evaluator. `inspect_swe` covers Claude Code, Codex, Gemini CLI, Kimi,
    OpenCode, mini-SWE-agent and Antigravity, but not Pi.
  - Epoch reducers include pass_at_k and pass_k_k. Clustered and bootstrap standard
    errors are available.
  - Score edits leave an append-only audit trail.
  - Sources: [agent bridge](https://inspect.aisi.org.uk/agent-bridge.html),
    [metrics](https://inspect.aisi.org.uk/metrics.html),
    [inspect_swe](https://meridianlabs-ai.github.io/inspect_swe/).
- **SWE-bench** only grades predictions. It caches by `run_id`, so a reused run id
  silently returns stale results
  ([guide](https://github.com/SWE-bench/SWE-bench/blob/main/docs/guides/evaluation.md)).
- **OpenAI hosted Evals** became read-only on 2026-10-31 and shuts down on 2026-11-30
  ([guide](https://developers.openai.com/api/docs/guides/evals)).
- **DSPy/GEPA** selects candidates on the validation set. That set is not a held-out
  estimate, so a separate untouched test split is required
  ([DSPy GEPA](https://dspy.ai/current/api/optimizers/GEPA/overview/),
  [paper](https://arxiv.org/abs/2507.19457)).
- **Guidance from Anthropic.**
  - Start with 20–50 tasks drawn from real failures.
  - Run several trials per task, grade outcomes rather than paths, and read
    transcripts.
  - Separate capability evals from regression evals. Use pass@k for capability and
    pass^k for reliability.
  - Source: [Demystifying evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).
- **Infrastructure noise.** Resource configuration alone moved Terminal-Bench by about
  6 points. Pin resources and record them
  ([Anthropic](https://www.anthropic.com/research/infrastructure-noise), via a
  secondary summary).
- **Harness effects.** LangChain gained 13.7 points on Terminal-Bench 2.0 by changing
  only the harness: self-verification, loop detection and a pre-completion checklist.
  It warns that changes overfitted to individual tasks regress elsewhere
  ([LangChain](https://www.langchain.com/blog/improving-deep-agents-with-harness-engineering)).

**Strength.** Agent Braid's registered cohorts, its D3 lineage rule, Clopper-Pearson
intervals, paired comparison and human per-axis promotion are stricter than what the
platforms below ship.

**Gaps.**
- One lineage with 5 cases makes every verdict structurally impossible.
- There is no regression gate.
- There is no task QA (oracle and exploit checks).
- Infrastructure errors are not separated from agent failures.
- Each host needs its own laboratory, instead of reusing adapters that already cover
  four of the five target hosts.

### 3. Promotion

All four server platforms (Langfuse, LangSmith, Braintrust, Phoenix) store immutable
versions and promote them by moving a pointer:

| Platform | Pointer | Access control |
|---|---|---|
| Langfuse | Labels (`production`, `staging`, `prod-a/b`) | Protected labels |
| LangSmith | Commit tags with environment history | Owner-only promotion |
| Braintrust | First-class environments (`bt prompts assign … --environment production`) | — |

Rollback means repointing. CI gates are score thresholds. None of them documents a
paired significance test in the product. promptfoo reports Wilson intervals on
repeated runs. LangSmith shows the standard deviation across repetitions.

Sources: [Langfuse](https://langfuse.com/docs/prompt-management/features/prompt-version-control),
[LangSmith](https://docs.langchain.com/langsmith/manage-prompts),
[Braintrust](https://docs.braintrust.dev/deploy/environments),
[promptfoo](https://www.promptfoo.dev/docs/guides/evaluate-llm-temperature/).

**Strength.** Exact candidate hashes and human promotion records.

**Gap.** There is no pointer model, so promoting and rolling back are not single,
auditable operations.

### 4. Isolation

- **Evaluation:** a container per trial from a pinned image, with a fresh filesystem
  each time (Harbor, Inspect, SWE-bench).
- **Daily use:** the host's own sandbox.

  | Host | Sandbox |
  |---|---|
  | Claude Code | OS sandbox (bubblewrap on Linux), managed sandbox keys ([managed settings](https://code.claude.com/docs/en/managed-settings)) |
  | Codex | `read-only` / `workspace-write` / `danger-full-access`, network off by default, Seatbelt on macOS and bubblewrap on Linux ([sandboxing](https://learn.chatgpt.com/docs/sandboxing)) |
  | ThinkRail | git worktrees |
  | Pi | None by design; it relies on external containerization |

- **Anthropic:** filesystem plus network isolation cut permission prompts by 84 %
  ([sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing)).

**Gap.** Agent Braid's own macOS `sandbox-exec` with a dedicated user is qualified per
OS build and CLI version, and an operating-system update voided it once. The field
uses containers to isolate evaluations and native sandboxes to isolate daily use.

### 5. Telemetry

- **OTel GenAI semantic conventions** define `invoke_agent` and `execute_tool` spans
  and attributes such as `gen_ai.agent.version`. Status: development
  ([OTel](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md)).
- **Claude Code** OTel attributes include `skill.name`, `plugin.name` and `agent_id`
  ([monitoring](https://code.claude.com/docs/en/monitoring-usage)).
- **Codex** has an `[otel]` exporter that is off by default
  ([config](https://learn.chatgpt.com/docs/config-file/config-advanced)).
- **All five platforms** ingest OTLP.

**Gap.** Agent Braid's local closed-vocabulary store has no OTel alignment, and the
harness candidate hash is not a standard attribute.

### 6. Harness engineering practice

These practices recur across sources:
- durable state outside the context window (progress files, a JSON feature list,
  execution plans);
- verification before declaring a task done;
- short root instructions;
- computational guides and sensors;
- an app the agent can observe;
- git as rollback.

Sources: [Anthropic long-running harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents),
[context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents),
[OpenAI](https://openai.com/index/harness-engineering/),
[Böckeler](https://martinfowler.com/articles/harness-engineering.html),
[12-factor agents](https://github.com/humanlayer/12-factor-agents).

Anti-patterns these sources warn against:
- encyclopedic instruction files;
- bloated tool sets;
- self-grading by the agent;
- premature "done";
- graders that check rigid tool-call order;
- unrecorded infrastructure.

## Options and owner decisions (2026-11-22)

| Id | Option | Owner decision |
|---|---|---|
| F1 | Read-only `harness` Agent Skill over the CLI in every host. A new ADR on portability tiers. ADR 0043 (MCP) stays rejected | Adopted |
| F2 | Hybrid evaluation substrate: Harbor containers for cross-host statistics, plus a small macOS shadow on SPEC-065 containment for fidelity | Adopted (ADR needed; supersedes the "own lab per host" part of ADR 0035 once accepted) |
| F3 | Capability versus regression evals: a regression gate on 20–50 real-failure tasks, ≥5 trials, paired, task-clustered errors; D3 kept for utility claims | Adopted |
| F4 | OTel GenAI telemetry with the candidate hash as `gen_ai.agent.version`; local first, OTLP opt-in, content redacted | Adopted |
| F5 | Promotion pointers (experimental, candidate, adopted) over immutable hashes; owner-only moves, append-only history | Adopted |
| F6 | Task QA and infrastructure controls: an oracle must pass and an exploit must fail; infrastructure errors kept separate; pinned resources and effort; fresh run ids | Adopted |
| — | Pi and ThinkRail as a host-integration spec after alpha.10 | Adopted |

The owner also decided that this round covers documentation only: research, ADRs,
specs, tasks and GitHub tracking. Code waits for each spec's approval.

## Limits

- Most sources are vendor documentation, read once on 2026-11-22.
- Some pages were read through an extraction service and some only as search
  snippets. The radar entries mark these as secondary.
- No tool was installed or run, and nothing was reproduced.
- The infrastructure-noise figures come from a secondary summary.
- The ThinkRail–ACP relationship and Pi's core `mcp.json` support are unverified.
- OpenCode's plugin package name is inconsistent between its docs and community guides.
