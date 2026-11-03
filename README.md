# Agent Braid

<p align="center">
  <img src="reports/assets/agent-braid-concurrency-cover-centered.png"
       alt="Concurrent computational paths crossing, separating and rejoining"
       width="960">
</p>

<p align="center"><strong>Coordinate AI coding agents on evidence, not trust.</strong></p>

<p align="center">
  <a href="https://github.com/jayanez/agent-braid/actions/workflows/validate.yml"><img src="https://github.com/jayanez/agent-braid/actions/workflows/validate.yml/badge.svg?branch=develop" alt="Develop validation"></a>
  <a href="pyproject.toml"><img src="https://img.shields.io/badge/Python-3.12%2B-3776AB" alt="Python 3.12 or newer"></a>
  <a href="ROADMAP.md"><img src="https://img.shields.io/badge/status-research%20alpha-6f42c1" alt="Research alpha"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL%20%2B%20CC%20BY%20SA-2ea44f" alt="Split software and documentation licenses"></a>
</p>

<p align="center">
  <a href="pyproject.toml"><img src="https://img.shields.io/badge/core%20dependencies-zero-brightgreen" alt="Zero runtime dependencies in the core"></a>
  <a href="docs/tooling/README.md"><img src="https://img.shields.io/badge/MCP-stdio%20server-1f6feb?logo=modelcontextprotocol&logoColor=white" alt="MCP stdio server"></a>
  <a href="docs/tooling/NATIVE_PLUGINS.md"><img src="https://img.shields.io/badge/Codex-native%20plugin-412991?logo=openai&logoColor=white" alt="Native plugin for Codex"></a>
  <a href="docs/tooling/NATIVE_PLUGINS.md"><img src="https://img.shields.io/badge/Claude%20Code-native%20plugin-D97757?logo=anthropic&logoColor=white" alt="Native plugin for Claude Code"></a>
  <a href="https://github.com/jayanez/agent-braid/tags"><img src="https://img.shields.io/github/v/tag/jayanez/agent-braid?filter=agent-braid--v*&label=plugin" alt="Latest native plugin release tag"></a>
  <a href="docs/tooling/INSTALL.md"><img src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey" alt="macOS and Linux"></a>
  <a href="docs/tooling/TELEMETRY.md"><img src="https://img.shields.io/badge/telemetry-off%20by%20default-success" alt="Telemetry off by default"></a>
  <a href="docs/tooling/SYSTEM_ONE_SHADOW.md"><img src="https://img.shields.io/badge/System%20One-opt--in%20shadow-8250df" alt="Opt-in System One decision layer in shadow mode"></a>
</p>

<p align="center">
  <a href="#-quick-start">Quick start</a> ·
  <a href="#-how-it-works">How it works</a> ·
  <a href="#-scientific-foundations">Scientific foundations</a> ·
  <a href="#-documentation">Documentation</a> ·
  <a href="docs/STATUS.md">Project status</a>
</p>

When several AI coding agents work on the same codebase, the hard questions are
not about any single agent. They are about how their work interacts: which
changes touch the same resources, which must happen in a given order, whether a
different order would produce the same result, and what actually happened once
the work landed. Agent hosts usually leave these questions implicit. **Agent
Braid makes them explicit, answers them with checkable evidence and keeps that
evidence after the work is done.**

It treats agent work the way concurrency theory treats operations: as actions
with declared effects on shared state, whose order matters exactly when they do
not commute. Each task is described with **Agent Interaction Metadata (AIM)** —
what it reads, writes and creates, and under which conditions — so conflicts,
dependencies and safe orderings are computed rather than guessed.

Agent Braid also supports an opt-in **System One** decision layer in shadow mode:
a fast, on-device layer that is meant to answer routine coordination questions
from Agent Braid's own work history, while the exact analysis above (System 2)
keeps the final say. Today it only records structural decision episodes beside
each analysis so the owner can measure it; it has no learned model yet, never
changes a result and never grants authority.

## ✨ What Agent Braid gives you

- **See interactions before they collide.** An effect graph across agent tasks
  reports exact-resource conflicts and the order they impose, and answers
  `unknown` instead of guessing when the declared information is not enough.
- **Prove whether order matters.** For small sets of immutable Git commits, every
  admissible order is replayed in isolation and the resulting trees are compared,
  so order independence is observed, not assumed.
- **Execute only what was verified and authorized.** Verified plans run through an
  owned local Git runtime with a one-use operator grant, isolated preparation,
  serial publication and recovery after interruption. Agents can propose; only an
  explicit grant executes.
- **Keep a portable record.** Every result is a versioned report that states its
  inputs, method and limits, so another person or tool can reconstruct and check
  it.
- **Work where the agents already run.** Native plugins for Codex and Claude Code
  and a bounded six-tool stdio MCP server bring the same checks into the agent's
  own loop.
- **Try a decision layer without trusting it.** The opt-in System One shadow mode
  records one structural episode per analysis on this machine, with no names or
  paths, and reports counts only. Its reference backend abstains: there is no
  learned model, accuracy or calibration claim yet, and confidence never grants
  authority. See [System One shadow mode](docs/tooling/SYSTEM_ONE_SHADOW.md).
- **Study agent harnesses offline.** The experimental Braid Harness laboratory
  records, verifies and compares harness variants on deterministic fixtures, with
  no native host, no paid route and no promotion without a human decision. See
  [Harnessing](docs/tooling/HARNESSING.md).
- **Stay local and minimal.** The core uses only Python's standard library.
  Decision diagnostics, workload forecasting and usage telemetry are opt-in, off
  by default and never leave the machine automatically.

Beyond the core, Agent Braid includes research tools for studying agent work
itself: an offline laboratory for comparing agent-guidance variants, a closed
simulator for workloads with external effects, and evaluation contracts for
measuring real owned work. A read-only activity viewer, **Loom**, is in
development: its event contract, adapters and store are merged as library code,
and its loopback server and 3D braid view are not built yet. They share the same
rule as everything else: none of them can authorize execution on its own.

## 🚀 Quick start

Install the **native user plugin** for your agent host: it bundles its own
runtime, registers its skills and guides you through selecting repositories.
Git and the selected host (Claude Code, Codex or OpenCode) must already be installed.

> **⚡ One command, every host on your PATH**
>
> For **macOS arm64** and **Linux x86_64 (glibc 2.28+)**, with the bundled
> runtime: no Python needed. Other platforms (macOS x86_64, Linux arm64, WSL):
> use the [Python fallback install](docs/tooling/INSTALL.md).
>
> ```sh
> curl -fsSL \
>   https://raw.githubusercontent.com/jayanez/agent-braid/develop/install.sh \
>   | sh -s -- --host all
> ```
>
> Add `--ref agent-braid--v0.1.0-alpha.7` to pin a release. `--host all` also
> includes OpenCode when `opencode` is on your PATH, and `--host opencode` installs
> only that host. (`--host both` is a deprecated alias for `codex` + `claude`.)

Prefer the host's own commands? The script runs exactly these
([details](docs/tooling/NATIVE_PLUGINS.md)); they track the `plugin-dist` branch:

**Claude Code**

```sh
claude plugin install agent-braid \
  --marketplace 'https://github.com/jayanez/agent-braid.git#plugin-dist' --scope user
```

**Codex**

```sh
codex plugin marketplace add https://github.com/jayanez/agent-braid.git --ref plugin-dist
codex plugin add agent-braid@agent-braid
```

**OpenCode** (from `0.1.0-alpha.7`)

```sh
opencode plugin add 'github:jayanez/agent-braid#plugin-dist::path:plugins/agent-braid'
```

### Then, in three steps

**Set up once.** In Claude Code run `/agent-braid:setup`; in Codex select the Agent
Braid `setup` skill; in OpenCode the plugin registers the
`setup` skill and an `agent-braid-setup` command. Pick the repositories to
register, review the preview and confirm: nothing is registered without both.
After a registry change, reconnect MCP with the host's native reconnect or restart
(OpenCode: `opencode reload`).

Then ask your agent to analyze work with `/agent-braid:analyze` (in Codex, select
the skill with `$` or `/skills`; in OpenCode ask for the `analyze` skill, whose
invocation form in a live session is unobserved). The steps below show the
equivalent CLI output; they need the CLI from "Use the CLI directly" below
(`agent-braid` is `.venv/bin/agent-braid` there) and, for steps 2 and 3, the
tutorial fixture that defines `$DEMO_DIR`. The plugin calls the same core. The
step 2 replay and the step 3 checks can be re-run independently; the step 1
verdict follows from the footprints the tasks declare.

**1. Which tasks collide?** Each pair of tasks gets a verdict, a reason and, when
there is one, the shared resource. Two tasks that edit different files:

```bash
agent-braid analyze examples/analysis/file-edits.json --format text
```

```text
Agent Braid analysis sha256:216014b8a3c05cff6440665d9f13cc9da6524694286d0ada852ccc7dd875a366
Operations: 2  Pairs: 1
edit-readme / edit-roadmap: independent-candidate
  - Complete exact-resource footprints are disjoint.
  constraints: requires-execution-contract-before-parallelism
Execution authorization: false
```

Two tasks that both write `README.md`, with the JSON report's shared resource:

```bash
agent-braid analyze examples/analysis/file-edits-conflict.json --format text
agent-braid analyze examples/analysis/file-edits-conflict.json --format json
```

```text
Agent Braid analysis sha256:4f9e8796b5d9ee119355faea4b0e79ac9ef168dadbcc6118bc260fedc010cc92
Operations: 2  Pairs: 1
edit-readme / edit-readme-intro: conflicting
  - At least one exact shared resource has a write-like effect.
  constraints: serialize-or-isolate
Execution authorization: false
```

```text
      "classification": "conflicting",
      …
      "left": "edit-readme",
      "reasons": [
        "At least one exact shared resource has a write-like effect."
      ],
      "right": "edit-readme-intro",
      "sharedResources": [
        "repo://agent-braid/README.md"
      ]
```

`conflicting` means run them one after the other or in isolation; neither result
executes anything. See [Reading an analysis](#reading-an-analysis) for all four
outcomes.

**2. Does order matter? Replayed.** For two real Git commits, Agent Braid does not
guess: it applies both admissible orders in isolation and compares the resulting
trees. Create the two commits with the
[owned Git tutorial fixture](examples/runtime/README.md#create-the-fixture)
(`a.txt` and `b.txt`, one commit each), then:

```bash
agent-braid analyze-git "$DEMO_DIR/analysis.json" --format text \
  --provenance-output "$DEMO_DIR/provenance.json"
agent-braid plan-git "$DEMO_DIR/analysis.json" \
  --evidence-output "$DEMO_DIR/replay.json" > "$DEMO_DIR/advisory.json"
```

```text
Agent Braid analysis sha256:40aa80c6ef34781523002fe678e126b189de69326fa9625947ce33bd9380e769
Operations: 2  Pairs: 1
a / b: independent-candidate
  - Complete exact-resource footprints are disjoint.
  constraints: requires-execution-contract-before-parallelism
Execution authorization: false
```

The replay evidence in `replay.json` records both orders and the tree each produced
(lines kept verbatim, `…` marks what was left out):

```text
  "result": "equivalent-observed",
  "schedules": [
    {
      …
      "finalTree": "f4b354863caa9cea99b95422c9dab70465757d87",
      "order": [
        "a",
        "b"
      ],
      …
    },
    {
      …
      "finalTree": "f4b354863caa9cea99b95422c9dab70465757d87",
      "order": [
        "b",
        "a"
      ],
      …
```

Both orders gave the same tree. This covers tracked paths, modes and blobs for
these two commits only; it does not run project tests.

**3. Don't trust it, verify it.** `verify-git` rebuilds that replay from the
repository itself, and `verify` re-checks a portable certificate, in both cases
recomputing the result instead of reusing the producer's verdict:

```bash
agent-braid verify-git "$DEMO_DIR/replay.json" --repository "$DEMO_DIR/source"
agent-braid verify examples/contracts/0.2.0-draft/false-verdict.json
agent-braid verify examples/contracts/0.2.0-draft/altered-artifact.json
```

```text
{
  "checkedClaim": {
    "domain": "repository:sha256:e045dd1dc81772b29f4a0b620222056160611c66821fc3b4ab8edf92e50661cf:base:4a239f8c76dc54181a67de4fb033aca14770ca4c",
    "method": "exhaustive-finite-replay",
    "property": "tracked-tree-equivalence",
    "result": "equivalent-observed",
    "schedulesChecked": 2
  },
  "reason": "all bounded Git schedules were independently replayed; no execution authorization",
  "status": "verified"
}
{
  "reason": "producer verdict mismatch",
  "status": "rejected"
}
{
  "reason": "artifact digest mismatch",
  "status": "rejected"
}
```

Verifying grants nothing. Execution needs a one-use operator grant bound to the
exact plan digest, issued outside every agent tool, skill and command; the
[owned Git tutorial](examples/runtime/README.md) runs it end to end, from the
grant to a private result you can verify.

**Status of this install path.** The
[alpha.4 acceptance record](specs/046-native-ai-plugins/release-acceptance-alpha4.md)
covers a Claude Code update, a public-tag install and a Codex CLI install, removal
and reinstall. Interactive skill use and Linux execution were not observed, and the alpha.7
native installs, including the OpenCode install, have not yet been observed.

<details>
<summary><strong>Use the CLI directly (Python 3.12+)</strong></summary>

The plugin calls the same command-line core. Use it directly to script checks,
inspect reports or contribute. Five steps, each building on the previous one;
none needs a model, an API key or network access beyond the clone.

**1. Install and check.** A source install in an isolated environment.

```bash
git clone https://github.com/jayanez/agent-braid.git && cd agent-braid
python3 -m venv .venv && .venv/bin/python -m pip install --editable .
.venv/bin/agent-braid --help
```

**2. Can two agent tasks run in parallel?** Each task declares the files it
writes. These two edit different files:

```bash
.venv/bin/agent-braid analyze examples/analysis/file-edits.json --format text
```

```text
Agent Braid analysis sha256:216014b8a3c05cff6440665d9f13cc9da6524694286d0ada852ccc7dd875a366
Operations: 2  Pairs: 1
edit-readme / edit-roadmap: independent-candidate
  - Complete exact-resource footprints are disjoint.
  constraints: requires-execution-contract-before-parallelism
Execution authorization: false
```

**3. What does a collision look like?** Same two tasks, but both write `README.md`:

```bash
.venv/bin/agent-braid analyze examples/analysis/file-edits-conflict.json --format text
```

```text
Agent Braid analysis sha256:4f9e8796b5d9ee119355faea4b0e79ac9ef168dadbcc6118bc260fedc010cc92
Operations: 2  Pairs: 1
edit-readme / edit-readme-intro: conflicting
  - At least one exact shared resource has a write-like effect.
  constraints: serialize-or-isolate
Execution authorization: false
```

`conflicting` tells you to run them one after the other or in isolation. Neither
result executes anything; see [Reading an analysis](#reading-an-analysis) for all
four outcomes.

**4. Check evidence someone else produced.** A replay certificate records that
every admissible order of a small set of changes was replayed and gave the same
result. `verify` re-checks it without trusting the producer:

```bash
.venv/bin/agent-braid verify examples/contracts/0.2.0-draft/replay.json
```

```text
{
  "checkedClaim": { …, "result": "equivalent-observed", "schedulesChecked": 2 },
  "reason": "finite model evidence checked; no execution authorization",
  "status": "verified"
}
```

It holds only for the two orders it checked; it grants no execution permission.

**5. Execute only what was verified.** The [owned Git tutorial](examples/runtime/README.md)
creates two real commits, replays both orders, issues a one-use grant on the
exact plan digest and publishes a private result you can verify.

Requires Python 3.12+; Git analysis/replay and the owned runtime also need Git,
and private execution runs on Linux and macOS with POSIX file locking. Optional
local diagnostics are off by default: [telemetry](docs/tooling/TELEMETRY.md)
(`agent-braid telemetry status`) and
[System One shadow mode](docs/tooling/SYSTEM_ONE_SHADOW.md)
(`agent-braid system-one report`). Every other command is listed in
[Command line](#-command-line).

</details>

<a id="from-analysis-to-a-verified-private-result"></a>

## 🔀 How it works

![Agent Braid as the algebraic concurrency layer: parallel agents in the AI development lifecycle declare tasks; commutation analysis over declared effects and Git replay classifies each pair as independent-candidate (can run in parallel), ordered, conflicting (serialize or isolate) or unknown (keep exclusive ownership); a verified plan runs only after a one-use operator grant on the exact digest, through the owned Git runtime into a private result; telemetry, System One shadow mode, the Harness lab and the Loom viewer are opt-in, experimental or in development and cannot authorize execution](docs/assets/agent-braid-overview.svg)

In an AI development lifecycle (AIDLC), several agents plan, build, test and
review the same codebase at once. Agent Braid is the algebraic concurrency layer
between them: it models each agent task as an operation with declared effects on
shared state, works out which operations commute and can run in parallel, and
which need an order or isolation, and keeps the evidence.

Agents keep working in their own host. Agent Braid analyzes what they declare,
and only an operator grant on an exact plan digest can execute anything. Everything
else (telemetry, System One, the Harness laboratory and the Loom viewer) is opt-in,
experimental or still in development, and none of it can authorize execution.

<details>
<summary><b>Drill-down: analysis, authority and the System One shadow path</b></summary>

![Agent tasks flow through analyze-work, an advisory report and prepare to a one-use operator grant, then execute into a private result repository; a dashed System One shadow path copies each successful analysis into a structural episode, a local private store and a counts-only report, and never returns to the main path](docs/assets/agent-braid-system2-system-one.svg)

1. **Declare.** Agent tasks reach Agent Braid as AIM effect records or immutable Git commits.
2. **Analyze (System 2).** `analyze-work` builds the effect graph or replays Git orders and returns an advisory report: `independent-candidate`, `ordered`, `conflicting` or `unknown`, always with `executionAuthorization: false`.
3. **Prepare.** `prepare` turns a verified plan into an exact plan digest.
4. **Authorize.** Only a one-use operator grant on that exact digest can start execution. This is the authority boundary.
5. **Execute and check.** The owned local Git runtime prepares in isolation, publishes checkpoints serially to a private result repository, and supports `verify` and `recover`.
6. **System One shadow path (opt-in).** After a successful analysis the shadow observer copies the report off the request path into one structural episode (no names, paths or prompts), appends it to a private local store (4 MiB a day, 30 days) and exposes counts through `system-one report`. Nothing flows back into the report, the plan or the grant. See [System One shadow mode](docs/tooling/SYSTEM_ONE_SHADOW.md).

</details>

<details>
<summary><b>Drill-down: Braid Harness laboratory (experimental, offline)</b></summary>

![An admission grant lets harness prepare import a verified candidate into one new private directory; context assembly feeds a deterministic fixture runner with simulated containment; a native backend gate refuses until qualified; a hash-chained attempt journal feeds observation records, verifiers and cost reconciliation, then an evaluation report; promotion needs a human decision that is not delivered yet](docs/assets/agent-braid-harness.svg)

1. **Admit.** A single-use admission grant lets `harness prepare` import a verified candidate; its only effect is one new private directory.
2. **Attempt.** Context assembly feeds a deterministic fixture runner with `simulated` containment. A native Claude backend (SPEC-065) is built but refuses until it is qualified.
3. **Record.** Each attempt writes a hash-chained journal and observation records with loss and privacy accounting.
4. **Evaluate.** Verifiers and cost reconciliation produce an evaluation report (`harness evaluation-summary`, `harness compare`).
5. **No promotion yet.** No verdict promotes or activates a profile; the human promotion step is not delivered. See [Harnessing](docs/tooling/HARNESSING.md).

</details>

<details>
<summary><b>Drill-down: Loom activity viewer (in development)</b></summary>

![Agent Braid artifacts, and later host telemetry, pass through event adapters and a strict agent-braid-loom/v0.1 validator into a ring event store and a viewer model, all merged as library code; a loopback server and a Three.js braid viewer are planned](docs/assets/agent-braid-loom.svg)

1. **Collect.** Adapters turn Agent Braid reports and Git inputs into events; Claude Code hooks, OTLP and Codex telemetry adapters are planned.
2. **Validate and store.** A strict `agent-braid-loom/v0.1` validator, a bounded ring store and a pure viewer model are merged as library code.
3. **Show (planned).** A loopback-only server and a Three.js braid viewer for replay and live use are not built yet. The viewer will be read-only and makes no speedup claim. See [SPEC-061](specs/061-activity-viewer/spec.md).

</details>

Diagram sources live next to the images in [`docs/assets/`](docs/assets/): a small
Python generator for the overview and Archify JSON for the drill-downs; the earlier private-result flow stays available as a
[Mermaid diagram](reports/assets/agent-braid-private-result-flow.mmd).

<a id="reading-an-analysis"></a>

### Reading an analysis

A report describes evidence about the inputs and declared effects it actually
observed. `independent-candidate` means complete exact-resource footprints show
no write conflict in that domain; an execution contract is still required.
`ordered` records an explicit dependency path. `conflicting` means a shared
exact resource has a write-like effect. `unknown` means coverage or adapter
semantics do not justify a stronger result. None is an execution verdict.

Reports bind inputs, name the rule set and method, retain assumptions and
point-of-use constraints, and set `executionAuthorization: false`. See the
[analysis contract](schemas/0.1.0-alpha/analysis-report.schema.json) and
[AIM draft 0.2](docs/architecture/DRAFT_0_2.md).

<a id="cli-reference"></a>

## 🛠 Command line

The command surface is visible here; `agent-braid <command> --help` lists each
command's required artifacts, destinations and acknowledgements.

| Command | Purpose |
| --- | --- |
| `analyze`, `analyze-trace`, `analyze-git` | Analyze AIM records, explicitly mapped trace metadata, or stable Git snapshots with provenance. |
| `verify` | Verify a bounded certificate bundle. |
| `plan-git`, `verify-git`, `verify-plan` | Produce and reconstruct bounded Git replay evidence and advisory plans. |
| `prototype-git` | Compare isolated patch preparation with serial scratch integration in disposable state. |
| `propose-exchange`, `verify-exchange` | Produce and regenerate restricted anchored-sequence exchange evidence. |
| `prepare-git-run`, `execute-git-run`, `recover-git-run`, `verify-git-run` | Prepare, explicitly authorize, recover or verify the bounded local Git runtime. |
| `prepare-policy-run`, `verify-policy-plan`, `grant-policy-run`, `execute-policy-run`, `inspect-policy-run`, `recover-policy-run` | Prepare and reconstruct an operator policy, issue a digest-bound grant, then execute or inspect/recover the private result. |
| `system-one capabilities`, `system-one decide` | Inspect or run opt-in offline synthetic decision diagnostics. |
| `system-one report`, `system-one purge` | Count or delete the episodes recorded by the opt-in System One shadow mode (SPEC-066); both accept `--telemetry local`. |
| `forecast capabilities`, `forecast predict`, `forecast advice`, `forecast inspect`, `forecast export`, `forecast serve-mcp` | Run opt-in local numeric forecasts and heuristic advice, or serve them over a read-only stdio MCP transport. |
| `telemetry status`, `telemetry report`, `telemetry export`, `telemetry merge`, `telemetry purge`, `telemetry audit-logs` | Inspect, move or clear default-off local numeric telemetry; `audit-logs` is a read-only comparison of the plugin's host MCP logs with the local store. |
| `plugin setup` (including `--prune-stale`), `plugin discover`, `plugin doctor`, `plugin workspaces`, `plugin serve` | Configure and diagnose the native user plugin and its workspace registry; `--prune-stale` previews removing deleted worktree roots and unsafe registrations. |
| `tooling` | Experimental portable local AI tooling surface. |

System One shadow mode is off by default. After `plugin setup --system-one shadow` (or `python -m agent_braid.tooling_mcp --system-one shadow` for the standalone server) and a reconnect, each successful `analyze-work` call also appends one closed-vocabulary structural episode to `~/.local/share/agent-braid/system-one/`, with 30 UTC dates retained and no upload; the write runs on a background worker, off the request path, and is dropped when that worker is busy. Episodes include structural features (per-side effect kinds, resource classes and path-shape counts) and per-repository salted pseudonymous resource hashes; the salt and episodes stay on this machine and `system-one purge` removes both. Every MCP envelope stays byte-identical, the reference backend only abstains, and no execution authority changes.

The analyzer/runtime contract is `0.1.0-alpha`; AIM and certificate contracts
are `0.2.0-draft`; the package version is `0.1.0a2`. The native plugin is versioned
separately (latest published `0.1.0-alpha.7`, rollback target `0.1.0-alpha.6`); `plugin-status` reports
the package as `version` and the plugin as `pluginVersion`. The public CLI does not
expose source-ref promotion, arbitrary repository code execution, or provider
calls through the owned runtime.


## 🧪 Scientific foundations

Agent Braid is also a research programme with a clear question. It draws on
algebraic models of concurrency — commutation, confluence and the
order-independence of independent actions — and takes inspiration from the
**Yang–Baxter equation**, which characterises when different orderings of pairwise
exchanges lead to the same outcome. The project does **not** assume that such
structure exists in AI agent work: it investigates which classes of agent
interactions admit it, starting from finite, checkable cases such as the
`anchored-sequence-v1` structured exchange and its bounded braid-relation
controls. Yang–Baxter is a source of **inspiration** today, not a proved theorem
about agents.

Every claim is earned by defining its objects, operators, equivalence relation,
domain and evidence. Claims distinguish analogy, hypothesis, heuristic, empirical,
exhaustive-finite and formal results. Finite replay and structural checks support
only their declared domains; they establish neither production safety,
hidden-effect completeness, general confluence nor a general Yang–Baxter theorem.
Assurance labels are [compatibility classes](docs/architecture/ASSURANCE_LEVELS.md),
with the property, method, observation and execution contract stated separately. Results are tied to frozen candidates, and negative results are
published alongside positive ones: the runtime evaluation, for example, did not
demonstrate a useful parallel speedup, and the project says so. The
[Constitution](CONSTITUTION.md) is the normative authority; start with
[claim discipline](docs/theory/CLAIM_DISCIPLINE.md),
[operational semantics](docs/theory/OPERATIONAL_SEMANTICS.md),
[structured exchange semantics](docs/theory/STRUCTURED_EXCHANGE.md) and the
[mathematical foundations](MATHEMATICAL_FOUNDATIONS.md).

## 📚 Documentation

| Your next step | Start here |
| --- | --- |
| Build and verify a local result | [Owned Git tutorial](examples/runtime/README.md) · [Installation](docs/tooling/INSTALL.md) |
| Use it from Codex or Claude Code | [Native plugins](docs/tooling/NATIVE_PLUGINS.md) · [AI tooling guide](docs/tooling/README.md) |
| Understand architecture and limits | [Architecture](ARCHITECTURE.md) · [Git replay](docs/architecture/GIT_REPLAY.md) · [ADRs](docs/adr/) |
| Consume portable artifacts | [AIM](docs/architecture/AGENT_INTERACTION_METADATA.md) · [Certificates](docs/architecture/CONFLUENCE_CERTIFICATE.md) · [Schemas](schemas/) |
| Explore the laboratories | [Harnessing](docs/tooling/HARNESSING.md) · [Activity viewer spec](specs/061-activity-viewer/spec.md) · [System One](docs/system-one/README.md) |
| Turn on optional local diagnostics | [Telemetry](docs/tooling/TELEMETRY.md) · [System One shadow mode](docs/tooling/SYSTEM_ONE_SHADOW.md) · [Forecast operations](docs/forecast/OPERATIONS.md) |
| Reproduce experiments | [Bounded laboratory](research/lab/README.md) · [Experiment protocol](docs/experiments/PROTOCOL.md) · [External reproduction](docs/releases/EXTERNAL_REPRODUCTION.md) |
| Explore the research programme | [Research](RESEARCH.md) · [Mathematical foundations](MATHEMATICAL_FOUNDATIONS.md) · [References](research/REFERENCES.md) |
| Follow progress and direction | [Project status](docs/STATUS.md) · [Roadmap](ROADMAP.md) · [Open-tooling strategy](docs/strategy/OPEN_TOOLING_STRATEGY.md) |
| Contribute under the project rules | [Contributing](CONTRIBUTING.md) · [Governance](GOVERNANCE.md) · [Terminology](TERMINOLOGY.md) |

## 🤝 Contributing

Contributions are welcome in bounded adapters, reproducible controls,
counterexamples, interoperability, concurrency semantics, Git internals and
precise documentation. Read [CONTRIBUTING.md](CONTRIBUTING.md) for the
development setup and validation profiles, and use [SECURITY.md](SECURITY.md) to
report vulnerabilities.

```bash
.venv/bin/python -m pip install -r requirements-dev.txt -r requirements-speckit.txt
.venv/bin/python -m scripts.restore_public_spec_history
.venv/bin/python -m scripts.validate_change --base develop --profile quick
```

<details>
<summary><strong>Repository map</strong></summary>

```text
agent_braid/   Analyzer, Git replay, structured exchange, private runtime and MCP
docs/          Architecture, ADRs, operational guides, theory and release records
examples/      Portable fixtures, positive/negative controls and runtime tutorial
research/      Finite laboratory, hypotheses, benchmarks, counterexamples and radar
schemas/       Versioned machine-readable contracts
scripts/       Validation, capture, reproduction, profiling and tracking tools
specs/         Feature plans, frozen evidence, assurance and review records
```

</details>

<a id="citation-and-licensing"></a>

## 📄 Citation and licensing

Cite the relevant release or frozen evidence record alongside the repository;
machine-readable metadata is in [CITATION.cff](CITATION.cff).

Copyright © 2026 Juan Antonio Yáñez García. Software, schemas, executable examples
and automation use [AGPL-3.0-only](LICENSES/AGPL-3.0-only.txt); documentation and
research use [CC-BY-SA-4.0](LICENSES/CC-BY-SA-4.0.txt). The [license map](LICENSE),
[attribution notices](NOTICE) and [trademark policy](TRADEMARKS.md) define the
applicable terms and project identity.
