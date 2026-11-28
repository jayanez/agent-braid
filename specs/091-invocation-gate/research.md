# Research: SPEC-091

Sources labelled **repo**, **lab** (owner's local run store, counts only), **paper**, **abstract**, **docs**
(host documentation), **community** or **own calculation**. Preprint and community claims are leads.

## R1 — Two endpoints

v4 called `analyze-work` in 53 of 300 rollouts and 51 of those first requests were valid (repo). Authoring
validity and unprompted invocation need different levers; the product name was present in every v1 to v3
prompt and absent from every v4 prompt (repo). Seven differences confound v3 against v4 (diagnosis §2.2).

## R2 — Construct validity and labels

With a strong model, a prompt that lists every fact may not need a tool, so not calling can be correct
(2605.14038, ToolFailBench, When2Call; leads). It is a product failure only when Agent Braid adds something
the prose answer lacks. The owner stated on 2026-11-27 that labels are assigned before measurement (OD-B1, not yet committed; T001 records it). An invocation-only
reward teaches keyword-triggered calls (2609.16268, abstract), so gate B measures false positives too.

## R3 — Levers

- Skill description decides automatic loading and is truncated at 1,536 characters; MCP tools are deferred
  behind tool search unless a tool sets `anthropic/alwaysLoad`; server instructions (up to 4,096
  characters) say when to search; a `UserPromptSubmit` hook adds context deterministically and should be
  factual (docs). The current skill description is a generic sentence (repo, `integrations/agent-braid/skills/agent-braid-analyze/SKILL.md`).
- A forced-evaluation hook reached 100 % skill activation against 50 to 55 % on 22 prompts (community, small
  sample, earlier models). Always-on skills were listed 198 times and opened 0; path-gated skills 28 of 66
  (2610.14216, paper).
- Untested here: `alwaysLoad` for plugin-provided servers; the tool-search ranking is undocumented.

## R4 — Why the lab must change

The current lab disables `Read`, `Grep`, `Glob` and `Bash` and installs one plugin
(`scripts/spec069_native_runs.py`, repo). Without competing tools or skills, recall and false positives do
not describe a real session.

## R5 — Why the optimizer must reach beyond the body

The optimizer mutates only the skill body under fixed front matter (`agent_braid/lightning_resources.py`),
`target.kind` accepts only `skill` (`agent_braid/lightning_config.py`), and the `analyze-work` definition is
at about 1,499 of 1,500 tokens (ADR 0038 D12; `agent_braid/tooling_mcp.py` comment) (repo). One contrastive
rewrite of a description captures most of the gain; further iterations move F1 by less than 0.5 %
(2606.30775, paper).

## R6 — Sizes

Detecting a recall rise from 18 % to 30 % needs about 156 rollouts per arm one-sided at 80 % power without
clustering (own calculation); it treats rollouts as independent. With the item as the unit (OD-17) and
within-item correlation of 0.81 on v4 (the ANOVA ICC of per-prompt pass counts), the effective sample is close to the number of items. The development factorial at
about 25 prompts per cell is a pilot, not a gate.

## R7 — Official harness

`claude plugin eval` is described as running 3 runs per case with and without the plugin and a "must not
invoke" grader (docs, not exercised here). It is a possible non-gating contrast (OD-13).
