# Harness² source audit and Agent Braid fit

Date: 2026-10-20 (Europe/Madrid). Status: source audit complete within the stated boundary; implementation planning remains draft.
This report proposes directions; it does not adopt an architecture, admit a
model-backed experiment, or claim implementation or scientific acceptance.

## Source identity and observation boundary

- Upstream: <https://github.com/google-research/harness2>, inspected at
  `1cfe254e8d25b15f37048c3730134686abe60335` (shallow source clone).
- Agent Braid: public `develop`,
  `69e7d374e5aaf13376486664e7368711d9826e6f`.
- Paper: [Harness², v1](https://arxiv.org/html/2610.14224v1).
- Direct inspection covers core orchestration, editable surfaces, context
  assembly, proposal validation, selection/reflection, experience storage,
  resumability, accounting, substrate boundaries, setup/provenance documentation,
  and selected benchmark launch/read boundaries. This is a targeted integration
  audit, not an exhaustive security assessment of downloaded dependencies,
  provider services, or every bundled third-party runner.
- No upstream code has yet been imported by this planning packet. The owner
  explicitly authorized selective software/architecture/scaffolding adaptation;
  see the [reuse map](../specs/048-harness-variant-laboratory/upstream-adaptation.md). No benchmark dataset,
  provider-backed execution, cloud setup, package installation, or paid API
  experiment ran. No independent reproduction of the paper's results occurred.
- Context7 resolved `/google-research/google-research`; its documentation query
  failed with monthly quota exhaustion. It supplied no Harness² documentation.
  The standalone pinned source and primary publications support this report.
- This worktree contains only `.codegraph/.gitignore`, with no index database;
  bounded direct source reads/searches were used. No index was initialized.

## What creates value in Harness²

| Mechanism | Source | Integration value and limits |
|---|---|---|
| Propose–Probe–Compose | [`core/recursion.py`](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/core/recursion.py) | Separates general and domain proposals, observes executions on the current task, then composes edits using behavioral contrasts. This creates testable alternatives to editing a prompt by intuition. Contrastive observations do not establish causal attribution for each edit. |
| Bounded editable surface | [`core/tree.py`](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/core/tree.py) | Names allowed component paths, caps always-on text, checks skill/script references and Python syntax, and returns actionable proposal errors. Agent Braid can adapt the concept while keeping authorities, permissions and validators immutable. Syntax and path checks do not enforce runtime effects. |
| Evidence as browsable files | [`core/context.py`](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/core/context.py) | Short missions point to task, source, trajectories, deliverables, harness diffs and prior decisions. Per-observation truncation still exists. A file inventory does not prove that a model read or understood every item. |
| Separation of method, executor and task domain | [`core/spec.py`](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/core/spec.py), [`substrate/base.py`](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/substrate/base.py) | Typed seams make method experiments independent of a benchmark or host. Reuse Agent Braid's existing semantics and admission boundaries rather than importing an incompatible executor. |
| Delayed judging and anonymized selection | [`core/selection.py`](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/core/selection.py), [`core/judge.py`](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/core/judge.py) | Candidate IDs reduce explicit label bias; benchmark judging follows committed selection. Grader-output tripwires help detect known leakage patterns. These are useful controls, not a complete information-flow barrier or objective correctness oracle. |
| Experience grounded in an adoption record | [`core/library.py`](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/core/library.py) | Stores the full adopted harness plus cue, lesson and evidence. Domain-scoped chronological prefixes prevent later entries from reaching earlier online tasks. Agent Braid needs explicit applicability, retention, revocation and trust states before persistent reuse. |
| Explicit completion and resume checks | [`core/runmark.py`](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/core/runmark.py), [`core/schedule.py`](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/core/schedule.py), [`cli/run_sweep.py`](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/cli/run_sweep.py) | Completed markers, harness fingerprints, artifact checks, locked atomic summaries and run configuration checks avoid treating output presence as completion. Preserve the idea using complete immutable manifests and Agent Braid's established durable state semantics. |
| Auditable recursion accounting | [`core/ledger.py`](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/core/ledger.py) | Checks unique labels and the method identity of 4k rollouts and 3k improvement stages. This is accounting, not an enforced cash cap. Retries, selection and reflection need their stated separate accounting included in total cost. |

## Differences the proposed Agent Braid capability must address

1. **Retain a baseline and an abstention outcome.** `selection_pool` intentionally
   excludes reference runs. At k=1, `trivial_selection` delivers the sole valid
   final without a selector session. This faithfully implements the upstream
   method; it does not demonstrate improvement over the base. Agent Braid should
   allow keep-base, inconclusive and rejected outcomes under a frozen policy.
2. **Enforce execution boundaries outside editable instructions.** The reference
   Codex argv bypasses sandbox, approvals and hook trust. The experiment guide
   explicitly reports unrestricted network access and an observed rubric
   download. Prompt rules and grader-marker scans cannot replace isolation or
   controlled evaluation inputs. See
   [substrate/codex.py](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/substrate/codex.py)
   and [the experiment guide](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/docs/EXPERIMENTS.md).
3. **Treat candidate files as untrusted.** A synthetic local probe confirmed that
   `tree.read_tree` follows a symlink at an allowed script path and reads its
   external target. No secrets or real external files were used. A future import
   boundary must explicitly constrain resolved paths, symlinks, size and type;
   the lexical path allowlist alone does not supply containment. This probe
   demonstrates that helper's behavior, not a provider exploit or full attack.
4. **Bind the complete experiment identity.** Upstream has useful namespace and
   CLI configuration checks. Its run marker alone fingerprints harness bytes
   using a shortened SHA-1 and represents inherited base harnesses as `base`.
   It does not by itself bind source state, model/build, policy or permissions.
   Use a full manifest and verify it at each relevant consumer; do not describe
   every upstream cache as unbound, because the CLI checks additional identity.
5. **Report every attempted unit.** Upstream reports graded performance while
   excluding ungraded rows and incomplete tasks from that score denominator.
   Preserve unknown results, but also report registered, started, completed,
   failed, refused and ungraded denominators and their costs. Otherwise apparent
   quality gains can hide attrition. See
   [core/report.py](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/core/report.py).
6. **Keep license domains separate.** The main project uses Apache-2.0; its
   [dependency inventory](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/dependencies/README.md)
   describes separate benchmark/data licenses and a WorkBuddy territorial
   restriction concerning EU use. Do not assume that the main license covers
   those assets. The recommended internal pilot needs none of those datasets.

## Existing Agent Braid assets and the actual gap

| Existing source | Reuse opportunity | Boundary |
|---|---|---|
| `agent_braid/tooling_mcp.py`, `plugin_mcp.py` | Bounded analysis results, artifact references, immutable configured workspaces and explicit workspace selection | A new capability needs an explicit contract; existing tool availability does not authorize host orchestration or registry mutation. |
| `agent_braid/tooling_sessions.py` | Single dispatch, durable start markers, attempted denominators and an injected trusted outcome-verifier seam | It does not implement a native host, provider or human verifier. Existing pending acceptance cannot be inherited. |
| `agent_braid/git_runtime.py`, `runtime_scheduler.py`; ADRs 0019/0020 | Exact fixed-patch identity, owned runs, recovery and bounded preparation | The admitted runtime excludes arbitrary code, hooks, source promotion and new network effects. A Codex/Claude probing laboratory needs a separately reviewed execution contract. |
| `agent_braid/trace_adapter.py` | Trace import, provenance and explicit loss accounting | A transformed trajectory is an observation with limits, not proof of complete effects. |
| `agent_braid/system_one.py`; SPEC-028–033 | Optional advisory request/response patterns and refusal | Harness improvement does not require a learned decision model or imply model acceptance. |
| SPEC-044 cost/admission documents; SPEC-047 telemetry | Reuse applicable accounting definitions and privacy lessons | Daily aggregate telemetry is insufficient for paired task evaluation or causal attribution. No automatic consent or capture authority transfers. |

The credible differentiation hypothesis is that harness changes can be made
inspectable and constrained by declared effects, complete experiment identity,
abstention and independently checked outcomes. This remains a hypothesis about
utility and adoption; it is not a novelty or safety theorem.

## Adjacent primary research

[GEPA](https://arxiv.org/abs/2507.19457) already explores reflection over
trajectories, tested prompt updates and combination of complementary candidates.
[ACE](https://arxiv.org/abs/2510.04618) studies evolving context playbooks with
incremental reflection and curation. These make generic prompt optimization or
persistent lessons weak differentiation claims. Their reported gains have not
been reproduced here and cannot be transferred to Agent Braid.

Harness² is particularly relevant for same-task contrastive refinement without
ground-truth feedback inside that refinement loop, and for connecting it to a
persistent improvement library. Agent Braid should evaluate these mechanisms
selectively and compare against a static harness and a simpler intervention.

## Verification actually executed

- Existing upstream workflow suite in an isolated Python 3.13.11 environment:
  `/private/tmp/harness2-audit-py313-20261020/bin/python -m unittest discover -s tests -v`.
  Result: 5 tests passed (8.272 s). Raw log:
  [retained log](../specs/048-harness-variant-laboratory/research-evidence/upstream-workflow-py313.txt). The interpreter patch
  version was verified with the same environment's `python --version`.
- Synthetic local boundary probes: allowed-path symlink target read confirmed;
  base candidate absent from the final-selection pool confirmed. Probe record:
  [retained probes](../specs/048-harness-variant-laboratory/research-evidence/boundary-probes.json).
- Initial Agent Braid worktree preflight failed with `public repository contains
  unreachable objects`. A full independent public-develop clone and the documented
  `restore_public_spec_history.py` recovery were used. Its preflight passed and
  `git fsck --unreachable --no-reflogs` returned zero output lines.
- No native Codex/Claude qualification, human acceptance, benchmark reproduction,
  containment qualification or economic-utility result has been obtained.

## Interview decisions and next boundary

Confirmed by the owner: both internal and eventual product use, starting with
internal development; reuse existing Codex/Claude and environment with no new
spend. The owner asked for a fit-based recommendation before choosing success
criteria and autonomy.

Six directions were surfaced: advisory context changes; isolated same-task
variant probes; evidence-scoped lessons; session recovery; interaction-aware
coordination; broad recursive rewriting. The provisional recommendation combines
small isolated probes with explicit baseline retention and human promotion,
then admits persistent lessons only after a useful pilot. Recovery can supply
an initial case; broad rewriting remains a later alternative.

Owner decisions now confirmed: both target axes are co-primary; automatic isolated
trials with initial human promotion; no new spend; repository-derived cases chosen
by the planner. Synthetic scenarios and an optional future automatic-promotion
assessment are explicitly retained. The resulting draft is
[SPEC-048/049](../specs/048-harness-variant-laboratory/program.md), with 28
requirements/scenarios and 40 pending tasks across three milestones. No implementation acceptance is
claimed by that planning packet.

Delivery path: preserve the agreed idea and feature-local ADR proposal, validate
the planning candidate, and publish only the authorized new tracking scope in
`jayanez/agent-braid` with proposal-source links. The requested Market Trends Report template and
its retained PPTX were located; the presentation should summarize the agreed
decision and sources rather than introduce another independent source of truth.

The owner subsequently challenged the compact backlog and selected the product/lifecycle name **Braid Harness**. The [coverage audit](../specs/048-harness-variant-laboratory/capability-coverage.md) records the resulting implementation ownership and advanced capability scope. Harness² in this report identifies the upstream reference only.
