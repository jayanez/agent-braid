# Documentation map

Where each kind of information lives and which file is its authority. Map checked
against the tree on 2026-11-26 (`develop` at `02b19545`). Each fact has one home;
other pages link to it instead of repeating it.

## Authority by question

| Question | Authority |
| --- | --- |
| What may the project claim and decide? | [Constitution](../CONSTITUTION.md) (normative), [ADRs](adr/) |
| What does a feature require, and what is its task state? | `specs/NNN-*/spec.md` and `tasks.md`; [spec workflow](development/SPEC_KIT.md) |
| Which spec belongs to which milestone? | [github-tracking.json](development/github-tracking.json), rendered in the [spec and milestone index](development/SPEC_MILESTONE_INDEX.md); conventions in [GitHub tracking](development/GITHUB_TRACKING.md) |
| What is the current state, with dates and evidence? | [STATUS.md](STATUS.md); live issue state in the [GitHub milestones](https://github.com/jayanez/agent-braid/milestones) |
| What is planned next? | [ROADMAP.md](../ROADMAP.md) |
| What does a term mean? | [TERMINOLOGY.md](../TERMINOLOGY.md) |

## Top-level documents

| File | Purpose |
| --- | --- |
| [README.md](../README.md) | Product overview, install, quick start; links to status instead of repeating it |
| [ARCHITECTURE.md](../ARCHITECTURE.md) | System architecture |
| [RESEARCH.md](../RESEARCH.md), [MATHEMATICAL_FOUNDATIONS.md](../MATHEMATICAL_FOUNDATIONS.md) | Research programme and its mathematical basis |
| [CONTRIBUTING.md](../CONTRIBUTING.md), [GOVERNANCE.md](../GOVERNANCE.md), [SECURITY.md](../SECURITY.md) | Contribution rules, decision rights, vulnerability reporting |
| [AGENTS.md](../AGENTS.md), [CLAUDE.md](../CLAUDE.md) | Instructions for coding agents working in this repository |

## `docs/` folders

| Folder or file | Purpose | Authority for |
| --- | --- | --- |
| [STATUS.md](STATUS.md) | Dated current state and evidence record | Status of every milestone and release |
| [adr/](adr/) | Architecture decision records | Decisions and their status |
| [architecture/](architecture/) | AIM, certificates, Git replay, assurance levels | Contracts described in prose; schemas are in [`schemas/`](../schemas/) |
| [theory/](theory/) | Claim discipline, operational semantics, structured exchange | Meaning of claims and semantics |
| [vision/](vision/) | Project manifesto | Intent, not status |
| [strategy/](strategy/) | Open-tooling strategy, ecosystem, market, community, harness benchmark | Strategy positions |
| [development/](development/) | Spec workflow, validation profiles, GitHub tracking, founder decisions, delivery records | Contributor process and tracking data |
| [tooling/](tooling/README.md) | Plugin, MCP, install, telemetry, harness, Lightning, viewer, evaluation records | Behaviour of the tooling surface |
| [system-one/](system-one/README.md) | System One program records and addenda | System One planning and audit records |
| [forecast/](forecast/OPERATIONS.md) | Forecast operations | Forecast commands and limits |
| [experiments/](experiments/PROTOCOL.md) | Experiment protocol and proposals | Experiment procedure |
| [releases/](releases/) | Milestone closure records, publication audit, external reproduction | Historical closure records |
| [ideas/](ideas/) | Unadopted ideas | Nothing; not a commitment |
| [assets/](assets/) | Diagram sources and images used by the README | Diagram files |
| [ai-tooling-presentation.md](ai-tooling-presentation.md) | Presentation of the AI tooling work | Nothing; a summary |

## Outside `docs/`

| Folder | Purpose |
| --- | --- |
| [`specs/`](../specs/) | One folder per feature: spec, plan, tasks, assurance and evidence |
| [`schemas/`](../schemas/) | Versioned machine-readable contracts |
| [`examples/`](../examples/) | Fixtures, controls and the runtime tutorial |
| [`research/`](../research/) | Laboratory, hypotheses, benchmarks, radar |
| [`scripts/`](../scripts/) | Validation, capture, reproduction and tracking tools |
| [`agent_braid/`](../agent_braid/) | Python package |
